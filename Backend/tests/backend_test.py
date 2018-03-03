from oeda.rtxlib.executionstrategy.MlrStrategy import start_mlr_mbo_strategy
import numpy as np
from uuid import uuid4
from rpy2.robjects import default_converter, pandas2ri
from rpy2.robjects.conversion import localconverter
import pandas as pd


def test_numpy_reciprocal(x):
    r = np.reciprocal(x)
    print(r)


def test_mlr_mbo():
    wf = dict(execution_strategy=dict(knobs=dict()), primary_data_provider=dict(), id=str(uuid4()))
    wf["primary_data_provider"]["ignore_first_n_samples"] = 20
    wf["execution_strategy"]["sample_size"] = 50
    wf["execution_strategy"]["optimizer_iterations"] = 3
    wf["execution_strategy"]["optimizer_random_starts"] = 2
    wf["execution_strategy"]["knobs"]["route_random_sigma"] = (0, 0.3)
    wf["execution_strategy"]["knobs"]["exploration_percentage"] = (1, 1.7)
    start_mlr_mbo_strategy(wf)


def test_pandas_conversion():
    x = dict(a=1, b=2, c=3)
    with localconverter(default_converter + pandas2ri.converter) as cv:
        pandas2ri.activate()
        c = pandas2ri.py2ri(x)
        print(c)


def test_pandas_df_conversion():
    pandas2ri.activate()
    wf = dict(execution_strategy=dict(knobs=dict()))
    df = pd.DataFrame(wf)
    r_dataframe = pd.py2ri(df)
    print(type(r_dataframe))
    print(r_dataframe)


def test_converter():
    wf = dict(execution_strategy=dict(knobs=dict()))
    with localconverter(default_converter + pandas2ri.converter) as cv:
        res = cv.py2ri(wf)
        print(res)


if __name__ == '__main__':
    test_numpy_reciprocal(2.524243245)
    test_mlr_mbo()
