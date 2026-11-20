import os
import secrets
import html

from flask import (
    Flask, render_template, request, redirect, url_for, session, flash
)
from cpm_algorithm import calculate_cpm

app = Flask(__name__)


app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)


# --------------------------------
# Helper: parse an integer field with a readable error message
# --------------------------------

def parse_int(value, field_name):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be a whole number.")



def generate_mermaid_graph(activities):

    # Start the Mermaid flowchart
    graph = ["flowchart LR"]

    # Define the appearance of nodes
    graph.append(
        "classDef normal fill:#DDE6ED,stroke:#526D82,color:#27374D,stroke-width:1.5px"
    )

    graph.append(
        "classDef critical fill:#27374D,stroke:#27374D,color:#FFFFFF,stroke-width:3px"
    )

    # Give every activity a safe Mermaid ID
    activity_ids = {
        activity['name']: f"ACT{i}"
        for i, activity in enumerate(activities)
    }

    # Keep track of critical and normal activities
    critical_nodes = []
    normal_nodes = []

    # Create the activity nodes
    for activity in activities:

        name = html.escape(
            activity['name'].replace('"', "'")
        )

        node_id = activity_ids[activity['name']]

        label = (
            f"{name} "
            f"(Duration: {activity['duration']})"
        )

        graph.append(
            f'{node_id}["{label}"]'
        )

        if activity['TF'] == 0:
            critical_nodes.append(node_id)
        else:
            normal_nodes.append(node_id)

    # Apply styles to the nodes
    if critical_nodes:
        graph.append(
            "class " + ",".join(critical_nodes) + " critical"
        )

    if normal_nodes:
        graph.append(
            "class " + ",".join(normal_nodes) + " normal"
        )

    # Create the dependency arrows
    for activity in activities:

        current_id = activity_ids[activity['name']]

        for predecessor in activity['predecessors']:

            predecessor_id = activity_ids[predecessor]

            previous_activity = next(
                a for a in activities
                if a['name'] == predecessor
            )

            # Check whether this dependency belongs
            # to a critical path
            is_critical_edge = (
                previous_activity['TF'] == 0
                and activity['TF'] == 0
                and activity['ES'] == previous_activity['EF']
            )

            if is_critical_edge:
                graph.append(
                    f"{predecessor_id} ==> {current_id}"
                )
            else:
                graph.append(
                    f"{predecessor_id} --> {current_id}"
                )

    return "\n".join(graph)


@app.route('/', methods=['GET', 'POST'])
def index():

    if request.method == 'POST':

        project_name = request.form.get('project_name', '').strip()

        try:
            n = parse_int(request.form.get('activities', 0),
                          "Number of activities")

            if not project_name:
                raise ValueError("Project name is required.")

            if n < 1 or n > 100:
                raise ValueError("Enter between 1 and 100 activities.")

        except ValueError as error:
            flash(str(error))
            return redirect(url_for('index'))

        session.clear()

        session['project_name'] = project_name
        session['number_of_activities'] = n
        session['activities'] = []
        session['show_graph'] = 'graph' in request.form
        session['show_information'] = 'information' in request.form

        return redirect(url_for('activity'))

    return render_template('index.html')




@app.route('/activity', methods=['GET', 'POST'])
def activity():

    if 'project_name' not in session:
        return redirect(url_for('index'))

    activities = list(session['activities'])   # work on a COPY
    n = session['number_of_activities']
    current_index = len(activities)

    # All activities already entered -> go to the results
    if current_index >= n:
        return redirect(url_for('results'))

    template = 'lasat_activity.html' if current_index == n - 1 \
        else 'activity.html'

    if request.method == 'POST':

        try:
            name = request.form.get('activity_name', '').strip()
            duration = parse_int(request.form.get('duration', ''),
                                 "Duration")
            predecessors = list(dict.fromkeys(      # remove duplicates
                request.form.get('predecessors', '').split()
            ))

            if not name:
                raise ValueError("Activity name is required.")

            if any(a['name'] == name for a in activities):
                raise ValueError(f"Activity '{name}' already exists.")

            if duration < 0:
                raise ValueError("Duration cannot be negative.")

          
            known = {a['name'] for a in activities}

            if name in predecessors:
                raise ValueError("An activity cannot depend on itself.")

            unknown = [p for p in predecessors if p not in known]
            if unknown:
                raise ValueError(
                    "Unknown predecessor(s): " + ", ".join(unknown) +
                    ". A predecessor must be entered before the "
                    "activities that depend on it."
                )

            candidate = {
                'name': name,
                'duration': duration,
                'predecessors': predecessors
            }

            
            if current_index == n - 1:
                calculate_cpm(activities + [candidate])

            activities.append(candidate)
            session['activities'] = activities

            if len(activities) < n:
                return redirect(url_for('activity'))

            
            return redirect(url_for('results'))

        except (ValueError, TypeError) as error:
            flash(str(error))
            return redirect(url_for('activity'))

    return render_template(
        template,
        project_name=session['project_name'],
        current_activity=current_index + 1,
        total_activities=n
    )




@app.route('/results')
def results():

    if 'project_name' not in session:
        return redirect(url_for('index'))

    activities = session.get('activities', [])

    if len(activities) < session['number_of_activities']:
        return redirect(url_for('activity'))

    result = calculate_cpm(activities)
    mermaid_graph = generate_mermaid_graph(
    result['activities']
)

    return render_template(
    'results.html',
    project_name=session['project_name'],
    activities=result['activities'],
    critical_paths=result['critical_paths'],
    project_duration=result['project_duration'],
    show_graph=session['show_graph'],
    show_information=session['show_information'],
    mermaid_graph=mermaid_graph
)

if __name__ == '__main__':
    app.run(debug=True)
