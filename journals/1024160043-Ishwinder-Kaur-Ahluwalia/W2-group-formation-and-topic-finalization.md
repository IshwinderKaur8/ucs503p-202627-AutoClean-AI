# Week 2: Group Formation and Topic Finalization

| Field | Value |
|---|---|
| **Author** | Ishwinder Kaur Ahluwalia |
| **Roll Number** | 1024160043 |
| **Period** | 2026-08-03 to 2026-08-08 |
| **Course** | UCS503 – Software Engineering |
| **Milestone** | Group Formation, Topic Evaluation, and Project Finalization |

## Objectives

- Form a group of three members with complementary skills and effective communication.
- Evaluate potential project topics against the course's selection criteria.
- Finalize a project topic that is feasible within the available time and resources.
- Identify potential weaknesses and edge cases in the selected topic and consider appropriate mitigations.

## Work Done

- Formed a group of three members based on complementary skills, shared interest, and the ability to collaborate effectively.
- Discussed and evaluated three potential project topics.
- Compared the candidate topics in terms of scope, feasibility, usefulness, technical complexity, scalability, and potential risks.
- Selected **AutoClean AI**, an automated data preprocessing system for machine learning datasets.
- Identified potential limitations and edge cases in AutoClean AI, particularly around handling outliers and ensuring that automated preprocessing does not negatively affect dataset quality.
- Discussed possible mitigation strategies for the identified issues.

## Topic Evaluation and Decision

| Candidate Topic | Decision | Rationale |
|---|---|---|
| **AutoClean AI – Automated Data Preprocessing** | **Selected** | Feasible within the available development timeline, addresses a practical problem faced by machine learning developers, and has potential to reduce repetitive preprocessing effort. |
| **Smart Team Formation System using Skills and Personality Analysis** | **Rejected** | The initial scope was too broad for the available timeline. It also introduced challenges related to the reliability of self-reported skills and personality assessments. |
| **Cross-Application Activity Streak Platform** | **Rejected** | Integration across multiple applications introduces significant security, authentication, privacy, and access-control concerns, increasing the project's complexity. |

## Selected Project: AutoClean AI

**AutoClean AI** is intended to automate common data preprocessing tasks for machine learning datasets. The project aims to reduce the manual effort required to prepare datasets by identifying and handling common data-quality issues through an automated pipeline.

The initial focus will be on practical preprocessing operations that can be implemented using mature existing libraries and frameworks rather than developing new preprocessing algorithms from scratch.

### Initial Challenges Identified

- Detecting and handling outliers without unnecessarily removing valid data points.
- Selecting appropriate preprocessing techniques based on the characteristics of the dataset.
- Handling different data types and missing-value patterns.
- Avoiding automated transformations that could introduce bias or distort meaningful information.
- Keeping the initial scope small enough to deliver a usable increment within the course timeline.

### Initial Mitigation Approach

- Use established statistical and machine learning techniques for preprocessing rather than developing novel algorithms.
- Provide transparent preprocessing decisions where possible so users can understand what transformations were applied.
- Validate preprocessing results using measurable dataset-quality and model-performance metrics.
- Begin with a limited set of well-defined preprocessing operations and expand the system incrementally.

## Decisions and Rationale

- A three-member group was formed with emphasis on complementary skills and effective collaboration.
- Three candidate project topics were considered.
- **AutoClean AI** was selected because it provides a practical problem, has an achievable initial scope, and can be implemented using mature technologies.
- The scope will be deliberately constrained during the initial development phase to support rapid delivery and evaluation.
- Potential edge cases and limitations will be considered early rather than after implementation.

## Issues and Blockers

- The main challenge during topic selection was balancing project ambition with the available development timeline.
- The rejected topics introduced either excessive scope or security and privacy concerns.
- AutoClean AI also presents challenges around making automated preprocessing decisions without compromising data quality; these will need to be addressed during design and implementation.

## Learnings

- A technically interesting idea is not necessarily a suitable course project if its scope cannot be controlled.
- Security, privacy, and integration complexity should be considered during topic selection rather than after development begins.
- Identifying edge cases early can prevent major design changes later.
- Existing mature libraries can significantly reduce implementation time and allow the team to focus on engineering, integration, and evaluation.
- Project scope should be aligned with the available development timeline and the requirement to deliver measurable results.

## Next Steps

- Prepare an elevator pitch for **AutoClean AI**.
- Clearly define the problem statement and target users.
- Identify the core features for the initial usable increment.
- Define the proposed technology stack and system architecture.
- Establish measurable evaluation criteria.
- Document the project's advantages, limitations, future scope, and anticipated technical difficulties.

## Contribution

- Initially proposed a **Smart Team Formation System** using explainable AI to assist faculty in creating balanced student teams and allocating project tasks.
- During evaluation, identified limitations including the reliability of self-reported skill information, the possibility of socially desirable responses in personality questionnaires, and the broad scope of the proposed system.
- Based on these constraints and the available development timeline, supported the decision to pivot toward **AutoClean AI**, a project proposed by a team member.
- Participated in evaluating the selected project, identifying potential weaknesses, and discussing mitigation strategies for issues such as outlier handling and automated preprocessing decisions.