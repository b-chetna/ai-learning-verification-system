# AI Learning Verification System — Testing Report

## 1. Objective

The purpose of testing is to verify the main application workflows, including authentication, subject management, quiz creation, quiz attempts, and performance reporting.

Tests should be performed on the running application, and the actual result should be recorded.

## 2. Test Cases

| Test ID | Test Case                        | Expected Result                                                   | Actual Result  | Status     |
| ------- | -------------------------------- | ----------------------------------------------------------------- | -------------- | ---------- |
| T01     | Student login                    | Student dashboard opens                                           | To be recorded | Not Tested |
| T02     | Teacher login                    | Teacher dashboard opens                                           | To be recorded | Not Tested |
| T03     | Administrator login              | Administrator dashboard opens                                     | To be recorded | Not Tested |
| T04     | Add subject                      | Administrator can add an active subject                           | To be recorded | Not Tested |
| T05     | Request subject                  | Teacher's request is recorded                                     | To be recorded | Not Tested |
| T06     | Approve subject                  | Approved subject is assigned to teacher                           | To be recorded | Not Tested |
| T07     | Create quiz                      | Teacher can create a quiz draft                                   | To be recorded | Not Tested |
| T08     | Publish quiz                     | Published quiz becomes available to eligible students             | To be recorded | Not Tested |
| T09     | Attempt quiz                     | Student can submit answers and receive a score                    | To be recorded | Not Tested |
| T10     | Review answers                   | Student can view selected and correct answers                     | To be recorded | Not Tested |
| T11     | Request re-quiz                  | Student's request appears for teacher review                      | To be recorded | Not Tested |
| T12     | Generate quiz with AI            | Teacher can generate questions for a selected topic               | To be recorded | Not Tested |
| T13     | Generate AI hint                 | Student receives a hint without the correct answer being revealed | To be recorded | Not Tested |
| T14     | Teacher viewing Student reports  | Teacher receives report of the student                            | To be recorded | Not Tested |
| T15     | Parent viewing Student reports   | Parent receives report of the student                             | To be recorded | Not Tested |

## 3. Test Result Recording

After running each test, record the actual result.

Use the following statuses:

* **Pass:** The observed result matches the expected result.
* **Fail:** The feature produces an incorrect result or an error.
* **Not Tested:** The test has not yet been performed.

## 4. Conclusion

Testing helps verify the functionality and reliability of the AI Learning Verification System. Any failures should be documented, investigated, and retested after fixes are made.
