# Software Configuration Management

## 1. Introduction

Software Configuration Management (SCM) is the process of managing changes to software throughout its development. It helps developers maintain version history, collaborate effectively, and keep track of modifications.

For the AI Learning Verification System, Git and GitHub were selected as the primary SCM tools.

## 2. Tools Used

**Git:** A version control system used to track code changes, create commits, manage branches, and maintain project history.

**GitHub:** An online platform used to host the Git repository, share code, manage contributions, and review changes.

**Visual Studio Code:** The development environment used to edit the Python files and execute Git commands through the integrated terminal.

## 3. Repository Initialization

The project was initialized as a Git repository using `git init -b main`.

A `.gitignore` file was created to exclude Python cache files, virtual environments, local database files, uploaded files, and secrets from version control.

The initial application was committed using a descriptive Git commit message and pushed to the GitHub repository named `ai-learning-verification-system`.

## 4. Version Control

Git records project changes through commits. Each commit contains a snapshot of the tracked files and a message describing the changes.

Descriptive commit messages help developers understand the project's development history and identify relevant changes.

## 5. Branch Management

The `main` branch is intended to contain the integrated project.

Separate branches are used for independent tasks, such as application development, AI integration, and documentation.

This approach allows team members to work separately and review changes before integrating them into the main branch.

## 6. Team Collaboration

The project is developed by two team members.

Each member contributes to the repository through their own branch. Team members avoid editing the same files simultaneously where possible, reducing the risk of conflicting changes.

## 7. Pull Requests and Merging

Pull requests are used to propose changes from a development branch into `main`.

Before merging, the changes should be reviewed and tested. This provides an opportunity to identify errors and confirm that the changes are appropriate for the project.

## 8. Benefits of SCM

* Maintains a history of software changes.
* Supports collaborative development.
* Helps identify and review code modifications.
* Allows work to be developed on separate branches.
* Provides a central location for source code and project documentation.
* Makes it easier to identify which changes introduced a problem.

## 9. Conclusion

Git and GitHub provide version control, repository hosting, and collaboration support for the AI Learning Verification System. Using branches, commits, and pull requests helps the team organize its work and integrate changes systematically.
