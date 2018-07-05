from flask_restful import Resource
from oeda.controller.experiment_results import get_all_stage_data
import matplotlib.pyplot as plt
import traceback
import json
import numpy as np
from io import BytesIO
import statsmodels.api as sm
import base64
from oeda.databases import db


# https://www.pythonanywhere.com/forums/topic/5017/
# https://stackoverflow.com/questions/38061267/matplotlib-graphic-image-to-base64
class QQPlotController(Resource):

    availableScales = ["normal", "log"]

    def get(self, experiment_id, step_no, stage_no, distribution, scale, incoming_data_type_name):
        try:
            # required because we store them as number in db, but retrieve as string
            step_no = int(step_no)
            if str(scale).lower() not in self.availableScales:
                return {"error": "Provided scale is not supported"}, 404

            pts = []
            # this case corresponds to all stage data of the provided step
            if int(stage_no) == -1:
                steps_and_stages = get_all_stage_data(experiment_id=experiment_id)
                if steps_and_stages is None:
                    return {"error": "Data points cannot be retrieved for given experiment and/or stage"}, 404

                for stage_no in steps_and_stages[step_no]:
                    entity = steps_and_stages[step_no][stage_no]
                    if 'values' in entity:
                        if len(entity['values']) == 0:
                            pass

                        for data_point in entity['values']:
                            # there might be payload data that does not include the selected data type. filter them out
                            point = data_point["payload"].get(incoming_data_type_name)
                            if point:
                                pts.append(point)
            else:
                data_points = db().get_data_points(experiment_id=experiment_id, step_no=step_no, stage_no=stage_no)
                if data_points is None:
                    return {"error": "Data points cannot be retrieved for given experiment and/or stage"}, 404
                for data_point in data_points:
                    point = data_point["payload"].get(incoming_data_type_name)
                    if point:
                        pts.append(point)

            # create the qq plot based on the retrieved data against provided distribution
            array = np.asarray(pts)
            sorted_array = np.sort(array)
            if str(scale).lower() == "log":
                sorted_array = np.log(sorted_array)

            fig1 = sm.qqplot(sorted_array, dist=str(distribution).lower(), line='45', fit=True)
            buf1 = BytesIO()
            fig1.savefig(buf1, format='png')
            buf1.seek(0)

            figure_data_png = base64.b64encode(buf1.getvalue())
            buf1.close()
            fig1.clf()
            del fig1
            plt.close('all')
            return figure_data_png

        except Exception as e:
            tb = traceback.format_exc()
            print(tb)
            return {"message": e.message}, 404
