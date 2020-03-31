import os
import shutil

from git import Repo

from scripts import version
from scripts.conan_release import PrepareConanRelease
from scripts.documentation_release import PrepareDocumentationRelease
from scripts.utilities import read_file, check_step, replace_text_in_file, run, write_file, use_directory, \
    check_step_with_revert, assert_step


class PrepareRelease:
    def __init__(self, details):
        self.details = details

    def check_pre_conditions_for_publish(self):
        if self.details.push_to_production:
            repo = Repo(self.details.main_project_dir)
            assert_step(not repo.bare)

            assert_step((repo.active_branch.name == 'master'))

            # From https://stackoverflow.com/questions/31959425/how-to-get-staged-files-using-gitpython
            assert_step(len(repo.index.diff(None)) == 0, "there are un-committed changes to ApprovalTests.cpp")  # Modified
            assert_step(len(repo.index.diff("HEAD")) == 0, "there are un-committed changes to ApprovalTests.cpp")  # Staged

            # From https://stackoverflow.com/questions/15849640/how-to-get-count-of-unpublished-commit-with-gitpython
            assert_step(len(
                list(repo.iter_commits('master@{u}..master'))) == 0, "there are un-pushed changes in ApprovalTests.cpp")

            run(["open", "https://github.com/approvals/ApprovalTests.cpp/commits/master"])
            check_step("the builds are passing")

            run(["open", "https://github.com/approvals/ApprovalTests.cpp/blob/master/build/relnotes_x.y.z.md"])
            run(["open", F"https://github.com/approvals/ApprovalTests.cpp/compare/{self.details.old_version}...master"])
            check_step("the release notes are ready")

        run(["open", "https://github.com/approvals/ApprovalTests.cpp/issues"])
        check_step("any issues resolved in this release are closed")

        run(["open", "https://github.com/approvals/ApprovalTests.cpp/milestones"])
        check_step("the milestone (if any) is up to date, including actual version number of release")

    def update_version_number_header(self):
        with use_directory(self.details.approval_tests_dir):
            version_header = os.path.join("ApprovalTestsVersion.h")

            text = \
                F"""#ifndef APPROVALTESTS_CPP_APPROVALTESTSVERSION_H
#define APPROVALTESTS_CPP_APPROVALTESTSVERSION_H

#define APPROVALTESTS_VERSION_MAJOR {self.details.new_version_object['major']}
#define APPROVALTESTS_VERSION_MINOR {self.details.new_version_object['minor']}
#define APPROVALTESTS_VERSION_PATCH {self.details.new_version_object['patch']}
#define APPROVALTESTS_VERSION_STR "{version.get_version_without_v(self.details.new_version)}"

#define APPROVALTESTS_VERSION                                                  \\
    (APPROVALTESTS_VERSION_MAJOR * 10000 + APPROVALTESTS_VERSION_MINOR * 100 + \\
     APPROVALTESTS_VERSION_PATCH)

#endif //APPROVALTESTS_CPP_APPROVALTESTSVERSION_H
"""
            write_file(version_header, text)

    def create_single_header_file(self):
        os.chdir("../ApprovalTests")
        print(os.getcwd())
        run(["java", "-version"])
        run(["java", "-jar", "../build/SingleHpp.v.0.0.2.jar", self.details.release_new_single_header])
        text = read_file(self.details.release_new_single_header)
        text = \
F"""// Approval Tests version {self.details.new_version}
// More information at: https://github.com/approvals/ApprovalTests.cpp

{text}"""
        write_file(self.details.release_new_single_header, text)

    def update_starter_project(self):
        STARTER_PATH_OLD_SINGLE_HEADER = F"{self.details.starter_project_dir}/lib/{self.details.old_single_header}"
        STARTER_PATH_NEW_SINGLE_HEADER = F"{self.details.starter_project_dir}/lib/{self.details.new_single_header}"

        # Make sure starter project folder is clean
        with use_directory(self.details.starter_project_dir):
            # Delete untracked files:
            # - does not delete ignored files
            # - does not delete untracked files in new, untracked directories
            run(["git", "clean", "-f"])

            run(["git", "reset", "--hard"])

        shutil.copyfile(self.details.release_new_single_header, STARTER_PATH_NEW_SINGLE_HEADER)

        # Delete the last release:
        if os.path.exists(STARTER_PATH_OLD_SINGLE_HEADER):
            os.remove(STARTER_PATH_OLD_SINGLE_HEADER)

        # Update the version in the "redirect" header:
        replace_text_in_file(F"{self.details.starter_project_dir}/lib/ApprovalTests.hpp", self.details.old_version, self.details.new_version)

        # Update the version number in the Visual Studio project:
        replace_text_in_file(F"{self.details.starter_project_dir}/visual-studio-2017/StarterProject.vcxproj", self.details.old_single_header,
                             self.details.new_single_header)

    def check_starter_project_builds(self):
        with use_directory(F"{self.details.starter_project_dir}/cmake-build-debug"):
            run(["cmake", "--build", "."])

    def add_to_git(self):
        def add():
            run(["git", "add", "."])

        self.do_things_in_starter_project_and_main(add)

    def do_things_in_starter_project_and_main(self, function):
        with use_directory(self.details.starter_project_dir):
            function()
        with use_directory(self.details.main_project_dir):
            function()

    def check_changes(self):
        def revert():
            run(["git", "clean", "-fx"])
            run(["git", "reset", "--hard"])

        def revert_all():
            self.do_things_in_starter_project_and_main(revert)

        def do_nothing():
            pass

        check_step_with_revert("you are happy with the changes?", do_nothing)


    def prepare_everything(self):
        self.check_pre_conditions_for_publish()

        self.update_version_number_header()

        self.create_single_header_file()

        self.update_starter_project()
        self.check_starter_project_builds()

        PrepareConanRelease.update_conan_recipe(self.details)

        PrepareDocumentationRelease.update_features_page(self.details)
        PrepareDocumentationRelease.update_readme_and_docs(self.details)
        PrepareDocumentationRelease.prepare_release_notes(self.details)
        PrepareDocumentationRelease.regenerate_markdown()

        version.write_version(self.details.new_version_object)
        self.add_to_git()

        self.check_changes()

