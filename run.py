import os
from linkedin_resume import LinkedInResume
from linkedin_resume import getfilelist


if __name__ == '__main__':
    profile_folder = os.path.abspath(os.path.join(os.path.dirname(
        os.path.abspath(__file__)), "profiles"))
    file_path = os.path.join(profile_folder, "Jeffrey LaBauve.pdf")

    resume = LinkedInResume(file_path)
    resume.parse_pages()
    resume.parse()

    getfilelist(profile_folder)
