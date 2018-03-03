from oeda.rtxlib.executionstrategy.MlrStrategy import start_mlr_strategy
import numpy as np
from uuid import uuid4
from rpy2.robjects import default_converter, pandas2ri
from rpy2.robjects.packages import importr



def check_numpy_reciprocal(x):
    r = np.reciprocal(x)
    print (r)


def check_mlr_mbo():
    wf = dict(execution_strategy=dict(knobs=dict()), primary_data_provider=dict())
    wf["primary_data_provider"]["ignore_first_n_samples"] = 20
    wf["execution_strategy"]["sample_size"] = 50
    wf["execution_strategy"]["optimizer_iterations"] = 3
    wf["execution_strategy"]["optimizer_random_starts"] = 2
    wf["execution_strategy"]["knobs"]["route_random_sigma"] = (0, 0.3)
    wf["execution_strategy"]["knobs"]["exploration_percentage"] = (1, 1.7)
    start_mlr_strategy(wf, str(uuid4()))


# def check_conversion():
#     wf = dict(execution_strategy=dict(knobs=dict()))
#     x = dict(a=1, b=2, c=3)
#     with localconverter(default_converter + pandas2ri.converter) as cv:
#         pandas2ri.activate()
#         c = pandas2ri.py2ri(x)
#         print c


# def check_2():
#     pandas2ri.activate()
#     base = importr('base')
#     stats = importr('stats')
#     wf = dict(execution_strategy=dict(knobs=dict()))
#
#     df = pd.DataFrame(wf)
#     r_dataframe = pd.py2ri(df)
#     print(type(r_dataframe))
#     print(r_dataframe)

# def check_3():
#     x = dict(a=1, b=2, c=3)
#     wf = dict(execution_strategy=dict(knobs=dict()))
#     base = importr('base')
#
#     with localconverter(default_converter + my_converter + pandas2ri.converter) as cv:
#         res = cv.py2ri(wf)
#         print res



if __name__ == '__main__':
    check_numpy_reciprocal(2.524243245)
    check_mlr_mbo()
