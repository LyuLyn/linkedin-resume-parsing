import os
import pandas as pd
from pandas import ExcelWriter
from linkedin_resume import LinkedInResume
from linkedin_resume import getfilelist

import logging

LOG_LEVEL = logging.DEBUG

logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)
# log to the console
handler = logging.StreamHandler()
handler.setLevel(LOG_LEVEL)
formatter = logging.Formatter("  %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


PROFILE_FOLDER = os.path.abspath(os.path.join(os.path.dirname(
    os.path.abspath(__file__)), "profiles"))


def single_test():
    file_path = os.path.join(PROFILE_FOLDER, "Jeffrey LaBauve.pdf")
    resume = LinkedInResume(file_path)
    resume.parse_and_save()


def batch_test(filename="results.xlsx"):
    exp_dfs = []
    edu_dfs = []

    cetificates = []

    file_list = getfilelist(PROFILE_FOLDER)
    count = len(file_list)

    for index, file_path in enumerate(file_list):
        logger.info(f"Processing {index + 1}/{count}, {file_path}")
        resume = LinkedInResume(file_path)
        resume.parse()
        exp_df = resume.get_exp_df()
        edu_df = resume.get_edu_df()
        cetificate = resume.get_cetificate_status()

        if exp_df is not None:
            exp_dfs.append(exp_df)
        if edu_df is not None:
            edu_dfs.append(edu_df)

        cetificates.append(cetificate)

    logger.info(f"Combing all informations")

    exp_df_all = pd.concat(exp_dfs)
    edu_df_all = pd.concat(edu_dfs)

    cetificate_df = pd.DataFrame(cetificates)

    logger.info(f"Output to xlsx file {filename}")

    # pylint: disable=abstract-class-instantiated
    with ExcelWriter(filename) as writer:
        exp_df_all.to_excel(writer, sheet_name="experience")
        edu_df_all.to_excel(writer, sheet_name="education")
        cetificate_df.to_excel(writer, sheet_name="cetificate")

    logger.info(f"Done")


if __name__ == '__main__':
    # single_test()

    batch_test()
