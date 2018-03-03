from colorama import Fore
from oeda.log import *
from oeda.utilities.RUtility import install_packages
from oeda.rtxlib.execution import experimentFunction
from rpy2.rinterface import FloatSexpVector, ComplexSexpVector, StrSexpVector
from rpy2.robjects import default_converter, pandas2ri
from rpy2.robjects.conversion import Converter, localconverter

from rpy2.robjects.packages import importr
import rpy2.rinterface as ri
import rpy2.robjects as robjects
import random

global_wf_dict = dict()
variable = ""

# @robjects.conversion.py2ri.register(ComplexSexpVector)
# def complex_sexp_str(dictionary):
#     return ComplexSexpVector(dictionary)
#
# # method to return Python representation of R vectors
# @robjects.conversion.py2ri.register(FloatSexpVector)
# def tuple_str(tpl):
#     return FloatSexpVector(tpl)

def start_mlr_strategy(wf, experiment_id):
    """ executes a self optimizing strategy """
    info("> ExecStrategy   | MLR", Fore.CYAN)
    install_packages()
    mlr = importr('mlr')
    mlr_mbo = importr('mlrMBO')
    smoof = importr('smoof')
    lhs = importr('lhs')
    param_helpers = importr('ParamHelpers')
    base_package = importr('base')
    methods_package = importr('methods')

    optimizer_iterations = wf["execution_strategy"]["optimizer_iterations"]
    optimizer_random_starts = wf["execution_strategy"]["optimizer_random_starts"]
    wf["totalExperiments"] = optimizer_iterations + optimizer_random_starts # also include random starts to it

    global global_wf_dict
    global_wf_dict = wf
    # we look at the ranges the user has specified in the knobs
    knobs = wf["execution_strategy"]["knobs"]
    info("> knobs", Fore.CYAN)
    info(knobs, Fore.CYAN)

    my_converter = Converter('my converter')
    # my_converter.py2ri.register(dict, complex_sexp_str)
    # my_converter.py2ri.register(tuple, tuple_str)
    cv = localconverter(default_converter + my_converter + pandas2ri.converter)

    # we create a list of variable names and a list of knob (from,to)
    variables = []
    range_tuples = []
    # we fill the arrays and use the index to map from optimizer to variable
    for key in knobs:
        global variable
        variable = key
        variables += [key]
        range_tuples += [(knobs[key][0], knobs[key][1])]

    # create the Params based on provided variables and concat them using base
    param_list = []
    for idx, var in enumerate(variables):
        lower = range_tuples[idx][0]
        upper = range_tuples[idx][1]
        param = param_helpers.makeNumericParam(id=var, lower=lower, upper=upper)
        param_list = base_package.c(param_list, param)

    print(type(param_list))
    # ref: https://www.rdocumentation.org/packages/smoof/versions/1.5.1/topics/makeSingleObjectiveFunction
    # print(param_list)
    # print(type(param_list))
    obj_fcn = smoof.makeSingleObjectiveFunction(
                    name="my_fcn",
                    fn=self_optimizer_execution_function,
                    par_set=param_helpers.makeParamSet(
                        #params=param_list
                        param_helpers.makeNumericParam(id="x", lower=0, upper=5),
                        param_helpers.makeCharacterVectorParam(id="experiment_id", len=len(experiment_id), default=experiment_id),
                        # param_helpers.makeCharacterParam(id="experiment_id", default=experiment_id, ),
                        # param_helpers.makeDiscreteParam(id="experiment_id", values=str(experiment_id), default=str(experiment_id), tunable=False)
                    ),
                    has_simple_signature=False,
                    minimize=True)

    design = param_helpers.generateDesign(n=optimizer_random_starts, par_set=param_helpers.getParamSet(obj_fcn), fun=lhs.randomLHS)
    surr_km = mlr.makeLearner(cl="regr.km", predict_type="se", covtype="matern3_2")

    control = mlr_mbo.makeMBOControl()
    control = mlr_mbo.setMBOControlTermination(control, iters=optimizer_iterations)
    control = mlr_mbo.setMBOControlInfill(control, crit=mlr_mbo.makeMBOInfillCritEI())
    info(obj_fcn, Fore.GREEN)
    run = mlr_mbo.mbo(obj_fcn, design=design, learner=surr_km, control=control)
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
def self_optimizer_execution_function(x, experiment_id):
    if x:
        print("x: ", x, " type: ", type(x))
        print("exp_id: ", experiment_id, " type: ", type(experiment_id))
        global variable, global_wf_dict
        wf = global_wf_dict
        knobs = dict()
        knobs[variable] = x[0]
        print knobs
        exp = dict()
        # exp["ignore_first_n_samples"] = wf["primary_data_provider"]["ignore_first_n_samples"]
        exp["ignore_first_n_samples"] = 20
        exp["sample_size"] = wf["execution_strategy"]["sample_size"]
        exp["knobs"] = knobs
        # print(exp)
        #
        # # global_wf.setup_stage(global_wf, exp["knobs"])6
        # # create a new experiment to run in execution
        return float(experimentFunction(wf, exp))
