# AI Learning Verification System — Testing Report

## 1. Objective

The purpose of testing is to verify the main application workflows, including authentication, subject management, quiz creation, quiz attempts, and performance reporting.

Tests should be performed on the running application, and the actual result should be recorded.

## 2. Test Cases

| Test ID | Test Case                        | Expected Result                                                   | Actual Result                                                     | Status     |
| ------- | -------------------------------- | ----------------------------------------------------------------- | ----------------------------------------------------------------- | ---------- |
| T01     | Student login                    | Student dashboard opens                                           | Student dashboard opens                                           | Pass       |
| T02     | Teacher login                    | Teacher dashboard opens                                           | Teacher dashboard opens                                           | Pass       |
| T03     | Administrator login              | Administrator dashboard opens                                     | Administrator dashboard opens                                     | Pass       |
| T04     | Add subject                      | Administrator can add an active subject                           | Administrator can add an active subject                           | Pass       |
| T05     | Request subject                  | Teacher's request is recorded                                     | Teacher's request is recorded                                     | Pass       |
| T06     | Approve subject                  | Approved subject is assigned to teacher                           | Approved subject is assigned to teacher                           | Pass       |
| T07     | Create quiz                      | Teacher can create a quiz draft                                   | Teacher can create a quiz draft                                   | Pass       |
| T08     | Publish quiz                     | Published quiz becomes available to eligible students             | Published quiz becomes available to eligible students             | Pass       |
| T09     | Attempt quiz                     | Student can submit answers and receive a score                    | Student can submit answers and receive a score                    | Pass       |
| T10     | Review answers                   | Student can view selected and correct answers                     | Student can view selected and correct answers                     | Pass       |
| T11     | Request re-quiz                  | Student's request appears for teacher review                      | Student's request appears for teacher review                      | Pass       |
| T12     | Generate quiz with AI            | Teacher can generate questions for a selected topic               | Teacher can generate questions for a selected topic               | Pass       |
| T13     | Generate AI hint                 | Student receives a hint without the correct answer being revealed | Student receives a hint without the correct answer being revealed | Pass       |
| T14     | Teacher viewing Student reports  | Teacher receives report of the student                            | Teacher receives report of the student                            | Pass       |
| T15     | Parent viewing Student reports   | Parent receives report of the student                             | Parent receives report of the student                             | Pass       |

## 3. Test Result Recording

After running each test, record the actual result.

Use the following statuses:

* **Pass:** The observed result matches the expected result.
* **Fail:** The feature produces an incorrect result or an error.
* **Not Tested:** The test has not yet been performed.

## 4. Conclusion

Testing helps verify the functionality and reliability of the AI Learning Verification System. Any failures should be documented, investigated, and retested after fixes are made.
