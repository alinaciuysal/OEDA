from oeda.log import *


def applyInitKnobs(wf):
    """ we are done, so revert to default if given """
    if "pre_workflow_knobs" in wf.execution_strategy:
        try:
            info("> Applied the pre_workflow_knobs")
            wf.change_provider["instance"] \
                .applyChange(wf.change_event_creator(wf.execution_strategy["pre_workflow_knobs"]))
        except:
            error("apply changes did not work")


def applyDefaultKnobs(wf):
    """ we are done, so revert to default if given """
    if "post_workflow_knobs" in wf.execution_strategy:
        try:
            info("> Applied the post_workflow_knobs")
            wf.change_provider["instance"] \
                .applyChange(wf.change_event_creator(wf.execution_strategy["post_workflow_knobs"]))
        except:
            error("apply changes did not work")


''' re-creates knobs from defaultVariables e.g.{"name":...,"default":...}, {"name":...,"default":...}, {"name":...,"default":...} ...'''
def create_knob_from_default(wf):
    knob = {}
    for definition in wf._oeda_target["defaultVariables"]:
        key = definition["name"]
        value = definition["default"]
        knob[key] = value
    return knob