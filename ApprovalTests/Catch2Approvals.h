
#ifndef CATCHPLAYGROUND_CATCH2APPROVALS_H_H
#define CATCHPLAYGROUND_CATCH2APPROVALS_H_H
#include "namers/ApprovalNamer.h"

// <SingleHpp unalterable>
#ifdef APPROVALS_CATCH
#define CATCH_CONFIG_MAIN
#include "Catch.hpp"
struct Catch2ApprovalListener : Catch::TestEventListenerBase {
    using TestEventListenerBase::TestEventListenerBase;
    TestName currentTest;

    virtual void testCaseStarting(Catch::TestCaseInfo const &testInfo) override {

        currentTest.fileName = testInfo.lineInfo.file;
        ApprovalNamer::currentTest(&currentTest);
    }

    virtual void testCaseEnded(Catch::TestCaseStats const &testCaseStats) override {
        while (!currentTest.sections.empty()) {
            currentTest.sections.pop_back();
        }
    }

    virtual void sectionStarting(Catch::SectionInfo const &sectionInfo) override {
        currentTest.sections.push_back(sectionInfo.name);
    }

    virtual void sectionEnded(Catch::SectionStats const &sectionStats) override {
        currentTest.sections.pop_back();
    }
};

CATCH_REGISTER_LISTENER(Catch2ApprovalListener)

#endif
// </SingleHpp>
#endif //CATCHPLAYGROUND_CATCH2APPROVALS_H_H