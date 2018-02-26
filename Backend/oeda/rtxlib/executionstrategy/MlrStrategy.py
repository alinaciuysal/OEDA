from colorama import Fore
from oeda.log import *
from oeda.rtxlib.execution import experimentFunction
from rpy2.robjects.packages import importr, isinstalled
from rpy2.robjects.conversion import Converter
from rpy2.rinterface import FloatSexpVector

import rpy2.rinterface as ri
import rpy2.robjects as robjects

global_wf = None
global_var = None


# method to return Python representation of R vectors
def tuple_str(tpl):
    return FloatSexpVector(tpl)

# group conversion functions into one object
my_converter = Converter('my converter')
my_converter.py2ri.register(tuple, tuple_str)

def start_mlr_strategy(wf):
    """ executes a self optimizing strategy """
    info("> ExecStrategy   | MLR", Fore.CYAN)
    optimizer_iterations = wf.execution_strategy["optimizer_iterations"]
    optimizer_random_starts = wf.execution_strategy["optimizer_random_starts"]
    wf.totalExperiments = optimizer_iterations + optimizer_random_starts # also include random starts to it

    # we look at the ranges the user has specified in the knobs
    knobs = wf.execution_strategy["knobs"]
    info("> knobs", Fore.CYAN)
    info(knobs, Fore.CYAN)

    variable = ""
    range_tuples = ()
    # we create a list of variable names and a list of knob (from,to)
    # we fill the arrays and use the index to map from optimizer to variable
    for key in knobs:
        variable = key
        range_tuples = (knobs[key][0], knobs[key][1])
        info(variable, Fore.CYAN)
        info(range_tuples, Fore.GREEN)

    global global_var, global_wf
    global_var = variable
    global_wf = wf

    # ref: https://www.rdocumentation.org/packages/smoof/versions/1.5.1/topics/makeSingleObjectiveFunction
    install_packages()
    mlr = importr('mlr')
    mlr_mbo = importr('mlrMBO')
    smoof = importr('smoof')
    lhs = importr('lhs')
    param_helpers = importr('ParamHelpers')
    obj_fcn = smoof.makeSingleObjectiveFunction(
                    name="my_fcn",
                    fn=self_optimizer_execution_function,
                    par_set=param_helpers.makeNumericParamSet("x", len=1L, lower=range_tuples[0], upper=range_tuples[1]),
                    minimize=True)

    design = param_helpers.generateDesign(n=optimizer_random_starts, par_set=param_helpers.getParamSet(obj_fcn), fun=lhs.randomLHS)
    surr_km = mlr.makeLearner(cl="regr.km", predict_type="se", covtype="matern3_2")

    control = mlr_mbo.makeMBOControl()
    control = mlr_mbo.setMBOControlTermination(control, iters=optimizer_iterations)
    control = mlr_mbo.setMBOControlInfill(control, crit=mlr_mbo.makeMBOInfillCritEI())
    info(obj_fcn, Fore.GREEN)
    run = mlr_mbo.mbo(obj_fcn, design=design, learner=surr_km, control=control)
    # run = mlr_mbo.mbo(obj_fcn, control=control)
    info(">>>>>>>>>>> MLR RUN")
    info(run)

    # optimizer is done, print results
    # info(">")
    # info("> OptimalResult  | Knobs:  " + str(recreate_knob_from_optimizer_values(variables, optimizer_result.x)))
    # info(">                | Result: " + str(optimizer_result.fun))


''' installs required packages and libraries for executing R functions'''
def install_packages():
    packnames = ('ggplot2', 'smoof', 'mlr', 'mlrMBO', 'DiceKriging', 'randomForest', 'rPython', 'ParamHelpers', 'stats', 'rgenoud', 'lhs')

    if all(isinstalled(x) for x in packnames):
        have_tutorial_packages = True
    else:
        have_tutorial_packages = False

    if not have_tutorial_packages:
        # import R's utility package
        utils = importr('utils')
        # select a mirror for R packages
        utils.chooseCRANmirror(ind = 1) # select the first mirror in the list

        # R vector of strings
        from rpy2.robjects.vectors import StrVector
        # file
        packnames_to_install = [x for x in packnames if not isinstalled(x)]
        if len(packnames_to_install) > 0:
            utils.install_packages(StrVector(packnames_to_install))

def recreate_knob_from_optimizer_values(variables, opti_values):
    """ recreates knob values from a variable """
    knob_object = {}
    # create the knobObject based on the position of the opti_values and variables in their array
    for idx, val in enumerate(variables):
        knob_object[val] = opti_values[idx]
    return knob_object

''' this is the cost function callable from R and that returns a value for optimization '''
@ri.rternalize
def self_optimizer_execution_function(x):
    global global_wf
    global global_var
    exp = dict()
    exp["ignore_first_n_samples"] = global_wf.primary_data_provider["ignore_first_n_samples"]
    exp["sample_size"] = global_wf.execution_strategy["sample_size"]

    knobs = {}
    knobs[global_var] = x[0]
    exp["knobs"] = knobs
    global_wf.setup_stage(global_wf, exp["knobs"])
    # create a new experiment to run in execution
    return float(experimentFunction(global_wf, exp))