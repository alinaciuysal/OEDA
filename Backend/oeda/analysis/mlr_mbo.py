from rpy2.robjects.packages import importr, isinstalled
import rpy2.robjects as robjects
import rpy2.rinterface as ri

''' installs required packages and libraries for executing R functions  '''
def install_packages():
    packnames = ('ggplot2', 'smoof', 'mlrMBO', 'DiceKriging', 'randomForest', 'rPython', 'ParamHelpers', 'stats', 'rgenoud')

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


def run_mlr_using_robjects():
    importr('mlrMBO')

    # use a pre-defined function
    # robjects.r('obj.fun = makeCosineMixtureFunction(1)')

    # or create your own objective function
    # robjects.r('obj.fun = makeSingleObjectiveFunction(name = "my_sphere", fn = function(x) {sum(x*x) + 7}, par.set = makeParamSet(makeNumericVectorParam("x", len = 2L, lower = -5, upper = 5)),minimize = TRUE)')
    # example 2
    # robjects.r('obj.fun = makeSingleObjectiveFunction(name = "My fancy function name", fn = function(x) x * sin(3*x), par.set = makeNumericParamSet("x", len = 1L, lower = 0, upper = 2 * pi), minimize = TRUE)')

    robjects.r('obj.fun = makeSingleObjectiveFunction(name = "My fancy function name", fn = g, par.set = makeNumericParamSet("x", len = 1L, lower = 0, upper = 2 * pi), minimize = TRUE)')
    robjects.r('des = generateDesign(n = 5, par.set = getParamSet(obj.fun), fun = lhs::randomLHS)')
    robjects.r('des$y = apply(des, 1, obj.fun)')
    robjects.r('surr.km = makeLearner("regr.km", predict.type = "se", covtype = "matern3_2", control = list(trace = FALSE))')
    robjects.r('control=makeMBOControl()')
    robjects.r('control = setMBOControlTermination(control, iters = 10)')
    robjects.r('control = setMBOControlInfill(control, crit = makeMBOInfillCritEI())')
    run = robjects.r('run = mbo(obj.fun, design = des, learner = surr.km, control = control, show.info = TRUE)')
    print run


def run_mlr_using_rpy2():
    mlr_mbo = importr('mlrMBO')
    smoof = importr('smoof')
    param_helpers = importr('ParamHelpers')

    # cost function, callable from R
    @ri.rternalize
    def cost_f(x):
        # Rosenbrock Banana function as a cost function
        # (as in the R man page for optim())
        x1, x2 = x
        return 100 * (x2 - x1 * x1)**2 + (1 - x1)**2

    # call mlr's mbo function using our cost funtion
    obj_fcn = smoof.makeSingleObjectiveFunction(name="my_sphere",
                                      fn=cost_f,
                                      par_set=param_helpers.makeNumericParamSet("x", len=2L, lower=-5, upper=5),
                                      minimize=True)
    control = mlr_mbo.makeMBOControl()
    control = mlr_mbo.setMBOControlTermination(control, iters=10)
    control = mlr_mbo.setMBOControlInfill(control, crit=mlr_mbo.makeMBOInfillCritEI())
    run = mlr_mbo.mbo(obj_fcn, control=control)
    print run

if __name__ == '__main__':
    install_packages()
    run_mlr_using_rpy2()