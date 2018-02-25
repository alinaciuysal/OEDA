from colorama import Fore
from oeda.log import *
from oeda.rtxlib.execution import experimentFunction
from rpy2.robjects.vectors import FloatVector
from rpy2.robjects.packages import importr, STAP, isinstalled
import rpy2.robjects as robjects
import rpy2.rinterface as ri

global_wf = None
global_var = None

def start_mlr_strategy(wf):
    global global_wf
    global_wf = wf
    """ executes a self optimizing strategy """
    info("> ExecStrategy   | MLR", Fore.CYAN)
    wf.totalExperiments = wf.execution_strategy["optimizer_iterations"]
    optimizer_random_starts = wf.execution_strategy["optimizer_random_starts"]

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

    global global_var
    global_var = variable

    install_packages()
    mlr = importr('mlrMBO')
    smoof = importr('smoof')
    lhs = importr('lhs')
    param_helpers = importr('ParamHelpers')

    # call mlr's mbo function using our cost funtion
    # we give the function a callback to execute
    # it uses the return value to select new knobs to test
    # TODO: we optimize single variable for now
    # by default, minimize = True for makeSingleObjectiveFunction
    # obj_fcn = smoof.makeSingleObjectiveFunction(
    #             lambda opti_values: self_optimizer_execution(wf, opti_values, variables),
    #             param_helpers.makeNumericParamSet(variables[0], lower=range_tuples[0][0], upper=range_tuples[0][1]))
    obj_fcn = smoof.makeSingleObjectiveFunction(
                    name="my_fcn",
                    fn=self_optimizer_execution_function,
                    par_set=param_helpers.makeNumericParamSet("x", len=1L, lower=range_tuples[0], upper=range_tuples[1]),
                    minimize=True)
    info(obj_fcn, Fore.GREEN)
    # design = mlr.generateDesign(optimizer_random_starts, smoof.getParamSet(obj_fcn), lhs.randomLHS)
    # surr_km = mlr.makeLearner("regr.km", "cl", "se", covtype = "matern3_2", control = list(trace = FALSE))

    control = mlr.makeMBOControl()
    control = mlr.setMBOControlTermination(control, iters=wf.totalExperiments)
    control = mlr.setMBOControlInfill(control, crit=mlr.makeMBOInfillCritEI())
    run = mlr.mbo(obj_fcn, control=control)
    info(">>>>>>>>>>> MLR RUN")
    info(run)

    # optimizer is done, print results
    # info(">")
    # info("> OptimalResult  | Knobs:  " + str(recreate_knob_from_optimizer_values(variables, optimizer_result.x)))
    # info(">                | Result: " + str(optimizer_result.fun))

''' installs required packages and libraries for executing R functions'''
def install_packages():
    packnames = ('ggplot2', 'smoof', 'mlrMBO', 'DiceKriging', 'randomForest', 'rPython', 'ParamHelpers', 'stats', 'rgenoud', 'lhs')

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
    knobs[global_var] = x
    exp["knobs"] = knobs

    # create a new experiment to run in execution
    return float(experimentFunction(global_wf, exp))

# cost function, callable from R
@ri.rternalize
def cost_f(x):
    # Rosenbrock Banana function as a cost function
    # (as in the R man page for optim())
    x1, x2 = x
    return 100 * (x2 - x1 * x1)**2 + (1 - x1)**2

# cost function, callable from R (that did not work)
# @ri.rternalize
# def self_optimizer_execution(wf, opti_values, variables):
#     """ this is the function we call and that returns a value for optimization """
#     knob_object = recreate_knob_from_optimizer_values(variables, opti_values)
#     # create a new experiment to run in execution
#     exp = dict()
#     exp["ignore_first_n_samples"] = wf.primary_data_provider["ignore_first_n_samples"]
#     exp["sample_size"] = wf.execution_strategy["sample_size"]
#     exp["knobs"] = knob_object
#     return experimentFunction(wf, exp)