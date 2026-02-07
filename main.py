import glob
import json
import os
import yaml


CONTENT_FOLDER = "./ContentBundle"


def dump_json(data, path, indent=4):
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=indent, ensure_ascii=False)


def load_json_file(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def build_index(folder_path=CONTENT_FOLDER):
    index = {}

    for file_path in glob.glob(os.path.join(folder_path, "*.json")):
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                data = json.load(file)
        except Exception:
            continue

        filename = os.path.basename(file_path)
        prefix = filename.split("-", 1)[0]
        file_id = data.get("id")

        if file_id:
            index.setdefault(prefix, {})[file_id] = data

    for file_path in glob.glob(os.path.join(folder_path, "*.yml")):
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                data = yaml.safe_load(file)
        except Exception:
            continue

        if not data:
            continue

        filename = os.path.basename(file_path)
        prefix = filename.split("-", 1)[0]

        file_id = data.get("id") or data.get("commonfields", {}).get("id")

        if file_id:
            index.setdefault(prefix, {})[file_id] = data

    return index


def find_path(prefix, name, folder_path=CONTENT_FOLDER):
    pattern = os.path.join(folder_path, f"{prefix}-{name}.json")
    files = glob.glob(pattern)
    return files[0] if files else None


def find_playbook_tasks(playbook_data, index):
    tasks = playbook_data.get("tasks", {})
    sub_playbooks = []
    scripts = []

    for task_info in tasks.values():
        task = task_info.get("task", {})
        task_type = task.get("type")

        if task_type == "playbook":
            sub_playbook_id = task.get("playbookId")
            sub_playbook_data = (
                index.get("playbook", {}).get(sub_playbook_id)
                if sub_playbook_id
                else None
            )

            if sub_playbook_data:
                sub_tasks, sub_scripts = find_playbook_tasks(sub_playbook_data, index)

                entry = {
                    "id": sub_playbook_id,
                    "name": sub_playbook_data.get("name"),
                    "type": "playbook",
                }

                if sub_tasks:
                    entry["playbook"] = sub_tasks
                if sub_scripts:
                    entry["script"] = sub_scripts

                sub_playbooks.append(entry)

        elif task_type == "regular" and task.get("script"):
            script_id = task.get("script")
            script_data = index.get("automation", {}).get(script_id)

            if script_data:
                scripts.append(
                    {
                        "id": script_id,
                        "name": script_data.get("name"),
                        "type": "script",
                    }
                )

    return sub_playbooks, scripts


def main():
    # > Build Index
    print("Training arc in progress....")
    index = build_index()

    # > Get incident type and its content
    incident_type = input("Incident Type: ").strip()
    incident_type_path = find_path(prefix="incidenttype", name=incident_type)

    if not incident_type_path:
        print("NANI?! Unable to locate incident type!")
        return

    data = {incident_type: {}}
    incident_type_data = load_json_file(incident_type_path)

    # > Set layout
    layout_id = incident_type_data.get("layout")
    layout_data = index.get("layoutscontainer", {}).get(layout_id)

    data[incident_type]["layout"] = {
        "id": layout_id,
        "name": layout_data.get("name") if layout_data else None,
        "type": "layout",
    }

    # > Set post processing
    post_processing_id = incident_type_data.get("closureScript")
    post_processing_data = index.get("automation", {}).get(post_processing_id)

    data[incident_type]["post-processing"] = {
        "id": post_processing_id,
        "name": post_processing_data.get("name") if post_processing_data else None,
        "type": "post-processing",
    }

    # > Set playbook
    playbook_id = incident_type_data.get("playbookId")
    playbook_data = index.get("playbook", {}).get(playbook_id)

    playbook_info = {
        "id": playbook_id,
        "name": playbook_data.get("name") if playbook_data else None,
        "type": "playbook",
    }

    if playbook_data:
        sub_playbooks, scripts = find_playbook_tasks(playbook_data, index)

        if sub_playbooks:
            playbook_info["playbook"] = sub_playbooks
        if scripts:
            playbook_info["script"] = scripts

    data[incident_type]["playbook"] = playbook_info

    dump_json(data=data, path="outputs.json")
    print("Mission complete. Output written to outputs.json")


if __name__ == "__main__":
    main()
