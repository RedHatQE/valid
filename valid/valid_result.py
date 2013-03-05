def get_overall_result(ami):
    arch = ami["arch"]
    product = ami["product"]
    region = ami["region"]
    version = ami["version"]
    ami_result = ami["result"]
    overall_result = "succeeded"
    bug_summary = ami["ami"] + " " + product + " " + version + " " + arch + " " + region
    bug_description = ""

    for itype in ami_result.keys():
        bug_description += itype + "\n"
        itype_result = ami_result[itype]
        if type(itype_result) == dict:
            for stage in itype_result.keys():
                bug_description += stage + ":\n"
                stage_result = itype_result[stage]
                if type(stage_result) == dict:
                    for test in sorted(stage_result.keys()):
                        test_result = stage_result[test]
                        if type(test_result) == list:
                            is_failed = "succeeded"
                            for command in test_result:
                                if command["result"] in ["fail", "failed", "failure"]:
                                    is_failed = "failed"
                                    if overall_result == "succeeded":
                                        overall_result = "failed"
                                if command["result"] in ["skip", "skipped"]:
                                    is_failed = "skipped"
                            bug_description += "test %s %s\n" % (test, is_failed)
                            if is_failed != "succeeded":
                                for command in test_result:
                                    bug_description += "--->\n"
                                    for key in sorted(command.keys()):
                                        bug_description += "\t%s: %s\n" % (key, command[key])
                                    bug_description += "<---\n"
                else:
                    bug_description += "stage testing failed!\n"
                    overall_result = "failure"
        else:
            bug_description += "instance testing failed!\n"
            overall_result = "failure"
    bug_description = "Validation " + overall_result + " for " + ami["ami"] + " in " + region + " product: " + product + ", version: " + version + ", arch: " + arch + "\n\n" + bug_description
    return (overall_result, bug_summary, bug_description)
