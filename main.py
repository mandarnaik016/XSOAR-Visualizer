import glob
import json
import os
import yaml


def dump_json(data, path, indent=4):
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=indent, ensure_ascii=False)


def find_and_query_json(id, prefix, folder_path="./ContentBundle"):
    pattern = os.path.join(folder_path, f"{prefix}-*.json")
    matching_files = glob.glob(pattern)
    for file_path in matching_files:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
        if data.get("id") == id:
            return data
    return None


def find_and_query_yaml(id, prefix, folder_path="./ContentBundle"):
    pattern = os.path.join(folder_path, f"{prefix}-*.yml")
    matching_files = glob.glob(pattern)
    for file_path in matching_files:
        with open(file_path, "r", encoding="utf-8") as file:
            data = yaml.safe_load(file)
        if data and (
            data.get("commonfields", {}).get("id") == id or data.get("id") == id
        ):
            return data
    return None


def find_path(prefix, name, folder_path="./ContentBundle"):
    pattern = f"{folder_path}/{prefix}-{name}.json"
    files = glob.glob(pattern)
    return files[0] if files else None


def load_json_file(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)
    return data


def find_playbook_tasks(playbook_data):
    tasks = playbook_data.get("tasks", {})
    sub_playbooks = []
    scripts = []

    for task_id, task_info in tasks.items():
        task = task_info.get("task", {})
        task_type = task.get("type")

        if task_type == "playbook":
            sub_playbook_id = task.get("playbookId")
            sub_playbook_data = (
                find_and_query_yaml(id=sub_playbook_id, prefix="playbook")
                if sub_playbook_id
                else None
            )
            if sub_playbook_data:
                sub_playbook_name = sub_playbook_data.get("name")
                sub_playbook_tasks, sub_playbook_scripts = find_playbook_tasks(
                    sub_playbook_data
                )
                sub_playbook_entry = {
                    "id": sub_playbook_id,
                    "name": sub_playbook_name,
                    "type": "playbook",
                }
                if sub_playbook_tasks:
                    sub_playbook_entry["playbook"] = sub_playbook_tasks
                if sub_playbook_scripts:
                    sub_playbook_entry["script"] = sub_playbook_scripts
                sub_playbooks.append(sub_playbook_entry)

        elif task_type == "regular" and task.get("script"):
            script_id = task.get("script")
            script_data = (
                find_and_query_yaml(id=script_id, prefix="automation")
                if script_id
                else None
            )
            if script_data:
                script_name = script_data.get("name")
                scripts.append({"id": script_id, "name": script_name, "type": "script"})

    return sub_playbooks, scripts


def main():
    incident_type = input("Incident Type: ").strip()
    incident_type_path = find_path(prefix="incidenttype", name=incident_type)

    if incident_type_path:
        data = {}
        data[incident_type] = {}
        incident_type_data = load_json_file(incident_type_path)

        # > Layout
        layout_id = incident_type_data.get("layout")
        layout_data = (
            find_and_query_json(id=layout_id, prefix="layoutscontainer")
            if layout_id
            else None
        )
        layout_name = layout_data.get("name") if layout_data else None
        data[incident_type]["layout"] = {
            "id": layout_id,
            "name": layout_name,
            "type": "layout",
        }

        # > Post-Processing
        post_processing_id = incident_type_data.get("closureScript")
        post_processing_data = (
            find_and_query_yaml(id=post_processing_id, prefix="automation")
            if post_processing_id
            else None
        )
        post_processing_name = (
            post_processing_data.get("name") if post_processing_data else None
        )
        data[incident_type]["post-processing"] = {
            "id": post_processing_id,
            "name": post_processing_name,
            "type": "post-processing",
        }

        # > Playbook
        playbook_id = incident_type_data.get("playbookId")
        playbook_data = (
            find_and_query_yaml(id=playbook_id, prefix="playbook")
            if playbook_id
            else None
        )
        playbook_name = playbook_data.get("name") if playbook_data else None
        sub_playbooks, scripts = (
            find_playbook_tasks(playbook_data) if playbook_data else ([], [])
        )

        playbook_info = {"id": playbook_id, "name": playbook_name, "type": "playbook"}

        if sub_playbooks:
            playbook_info["playbook"] = sub_playbooks
        if scripts:
            playbook_info["script"] = scripts

        data[incident_type]["playbook"] = playbook_info

        dump_json(data=data, path="outputs.json")
    else:
        print("Unable to locate incident type!")


if __name__ == "__main__":
    main()
