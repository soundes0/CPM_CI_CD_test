
def calculate_cpm(activities):

    # 1. Validate and prepare activities
    activity_map = {}

    for activity in activities:
        name = activity['name'].strip()
        duration = int(activity['duration'])
        predecessors = activity.get('predecessors', [])

        if not name:
            raise ValueError("Activity name cannot be empty.")

        if name in activity_map:
            raise ValueError(f"Duplicate activity: {name}")

        if duration < 0:
            raise ValueError("Duration cannot be negative.")

        activity_map[name] = {
            'name': name,
            'duration': duration,
            'predecessors': list(dict.fromkeys(predecessors)),
            'ES': 0,
            'EF': 0,
            'LS': 0,
            'LF': 0,
            'TF': 0
        }

    # 2. Check dependencies
    for activity in activity_map.values():

        for predecessor in activity['predecessors']:

            if predecessor not in activity_map:
                raise ValueError(
                    f"Unknown predecessor: {predecessor}"
                )

            if predecessor == activity['name']:
                raise ValueError(
                    "An activity cannot depend on itself."
                )

    # 3. Topological sorting
    # This allows users to enter activities in any order.

    indegree = {
        name: len(activity['predecessors'])
        for name, activity in activity_map.items()
    }

    successors = {name: [] for name in activity_map}

    for name, activity in activity_map.items():
        for predecessor in activity['predecessors']:
            successors[predecessor].append(name)

    queue = [
        name for name in activity_map
        if indegree[name] == 0
    ]

    topo_order = []

    while queue:

        current = queue.pop(0)
        topo_order.append(current)

        for successor in successors[current]:

            indegree[successor] -= 1

            if indegree[successor] == 0:
                queue.append(successor)

    if len(topo_order) != len(activity_map):
        raise ValueError(
            "Circular dependency detected in activities."
        )

    # 4. Forward pass: ES and EF

    for name in topo_order:

        activity = activity_map[name]

        if not activity['predecessors']:
            activity['ES'] = 0

        else:
            activity['ES'] = max(
                activity_map[p]['EF']
                for p in activity['predecessors']
            )

        activity['EF'] = (
            activity['ES'] + activity['duration']
        )

    # 5. Project duration

    terminal = [
        activity_map[name]
        for name in activity_map
        if not successors[name]
    ]

    project_duration = max(
        activity['EF'] for activity in terminal
    )

    # 6. Backward pass: LS and LF

    for name in reversed(topo_order):

        activity = activity_map[name]

        if not successors[name]:
            activity['LF'] = project_duration

        else:
            activity['LF'] = min(
                activity_map[s]['LS']
                for s in successors[name]
            )

        activity['LS'] = (
            activity['LF'] - activity['duration']
        )

    # 7. Calculate total float

    for activity in activity_map.values():

        activity['TF'] = (
            activity['LS'] - activity['ES']
        )

    # 8. Find all critical paths

    critical_paths = []

    def find_paths(current, path):

        next_activities = [
            name for name in successors[current]
            if activity_map[name]['TF'] == 0
            and activity_map[name]['ES']
                == activity_map[current]['EF']
        ]

        if not next_activities:

            if activity_map[current]['EF'] == project_duration:
                critical_paths.append(path[:])

            return

        for next_activity in next_activities:
            find_paths(
                next_activity,
                path + [next_activity]
            )

    starting_activities = [
        name for name in topo_order
        if not activity_map[name]['predecessors']
        and activity_map[name]['TF'] == 0
    ]

    for start in starting_activities:
        find_paths(start, [start])

    # 9. Return results

    return {
        'activities': [
            activity_map[name] for name in activity_map
        ],
        'critical_paths': critical_paths,
        'project_duration': project_duration
    }
