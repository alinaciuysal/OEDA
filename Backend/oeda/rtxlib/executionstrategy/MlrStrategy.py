from colorama import Fore
from oeda.log import *
from oeda.utilities.RUtility import install_packages
from oeda.rtxlib.execution import experimentFunction
from rpy2.rinterface import ListSexpVector

from rpy2.robjects.packages import importr
import rpy2.rinterface as ri
import rpy2.robjects as robjects
import numpy as np

global_wf_dict = dict()

def start_mlr_mbo_strategy(wf):
    """ executes a self optimizing strategy """
    info("> ExecStrategy   | MLR", Fore.CYAN)
    install_packages()
    mlr_mbo = importr('mlrMBO')
    smoof = importr('smoof')
    lhs = importr('lhs')
    param_helpers = importr('ParamHelpers')

    optimizer_iterations = wf.execution_strategy["optimizer_iterations"]
    optimizer_iterations_in_design = wf.execution_strategy["optimizer_iterations_in_design"]
    wf.totalExperiments = optimizer_iterations + optimizer_iterations_in_design # also include number of samples in design to it

    # we look at the ranges the user has specified in the knobs
    knobs = wf.execution_strategy["knobs"]
    info("> knobs", Fore.CYAN)
    info(knobs, Fore.CYAN)

    # we create a list of variable names and a list of knob (from,to)
    variables = []
    range_tuples = []
    # we fill the arrays and use the index to map from optimizer to variable
    for key in knobs:
        variables += [key]
        range_tuples += [(knobs[key][0], knobs[key][1])]

    # also pass variables to global wf because we need it in objective function
    wf.variables = []
    wf.variables = variables
    global global_wf_dict
    global_wf_dict = wf
    # now create mbo parameters based on provided variables
    param_list = []
    for idx, var in enumerate(variables):
        lower = range_tuples[idx][0]
        upper = range_tuples[idx][1]
        param = param_helpers.makeNumericParam(id=var, lower=lower, upper=upper)
        param_list.append(param)

    # ref: https://www.rdocumentation.org/packages/smoof/versions/1.5.1/topics/makeSingleObjectiveFunction
    obj_fcn = smoof.makeSingleObjectiveFunction(
                    name="my_fcn",
                    fn=self_optimizer_execution_function,
                    par_set=param_helpers.makeParamSet(
                        params=[param for param in param_list]
                    ),
                    has_simple_signature=False,
                    noisy=True, # Our objective is the average trip overhead, which is only estimated, i.e. it's a noisy fcn
                    minimize=True)
    design = param_helpers.generateDesign(n=optimizer_iterations_in_design, par_set=param_helpers.getParamSet(obj_fcn), fun=lhs.randomLHS)
    # If no surrogate learner is defined, mbo() automatically uses Kriging for a numerical domain, otherwise random forest regression.
    # if you don't specify a learner in mbo() one is created depending on the structure of the problem
    # it also sets some other stuff if the function is noisy
    # surr_km = mlr.makeLearner(cl="regr.km", predict_type="se", covtype="matern3_2")

    control = mlr_mbo.makeMBOControl()
    control = mlr_mbo.setMBOControlTermination(control, iters=optimizer_iterations)
    control = mlr_mbo.setMBOControlInfill(control, crit=mlr_mbo.makeMBOInfillCritEI())
    # run = mlr_mbo.mbo(obj_fcn, design=design, learner=surr_km, control=control)
    run = mlr_mbo.mbo(obj_fcn, design=design, control=control)
    info(">>>>>>>>>>> MLR RUN")
    info(run)

    # optimizer is done, print results and remove wf from dict
    # global_wf_dict.pop(experiment_id)
    # global_variable_dict.pop(experiment_id)
    # print(global_wf_dict)
    # info(">")
    # info("> OptimalResult  | Knobs:  " + str(recreate_knob_from_optimizer_values(variables, optimizer_result.x)))
    # info(">                | Result: " + str(optimizer_result.fun))

''' this is the cost function callable from R and that returns a value for optimization '''
@ri.rternalize
def self_optimizer_execution_function(**kwargs):
    # convert provided Vector into Python list and create specific knob object to be passed
    knobs = dict()
    # provided kwargs is always like this: ('x', <rpy2.rinterface.ListSexpVector - Python:0x1203F090 / R:0x1F5C7D90>)
    # so, first extract the dict from kwargs and convert dict into numpy array and iterate further
    # https://stackoverflow.com/questions/16110715/getting-part-of-r-object-from-python-using-rpy2
    values = kwargs.get('x', None)
    values_array = np.asarray(values)

    global global_wf_dict
    wf = global_wf_dict
    variables = wf.variables
    assert(len(values_array) == len(variables))
    for idx, value in enumerate(values_array):
        variable_name = str(variables[idx])
        variable_value = value[0] # always float value is retrieved in 0-th element
        knobs[variable_name] = variable_value

    exp = dict()
    exp["ignore_first_n_samples"] = wf.primary_data_provider["ignore_first_n_samples"]
    exp["sample_size"] = wf.execution_strategy["sample_size"]
    exp["knobs"] = knobs
    wf.setup_stage(wf, exp["knobs"])
    # create a new experiment to run in execution
    return float(experimentFunction(wf, exp))
