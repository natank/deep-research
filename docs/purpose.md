in this workspace we will build a deep research app.
the app will allow user to input research topics and receive comprehensive summaries, relevant articles, and data visualizations. The goal is to streamline the research process, making it easier for users to gather information and insights efficiently.
the app should provide a web interface via browser, allowing users to interact with the app seamlessly. 
the app should be simple demo project that showcases the competency of the dev in building a full-stack llm provided application.

the app will follow the following process:
1. User inputs a research topic into the app.
2. the app plans the search list.
3. the app retrieves relevant articles and data from various sources.
4. the app generates a comprehensive report summarizing the findings, including key insights and data visualizations. the specific visualizations are left to design/implementation, this being a portfolio demo project.
5. the app sends the report to the user via email (simulated for demo purposes: the email send is simulated, and the UI shows a "email sent successfully" notification. after the notification, the report is made available to the user as a download in the UI, replacing an actual email delivery).

the search api will be made of the following components: ui, planner, searcher, writer, and emailer.

the app will use the OpenAI API for LLM capabilities (API key provided via .env), using the gpt-5.4-mini model to keep demo costs low. non-functional requirements (performance, cost, source limits, etc.) will otherwise follow reasonable defaults appropriate for a portfolio demo rather than production-grade targets.

we will follow the following structured approach to build the app:
0. Set up a github repo for the project and create a main branch for development with initial readme commit.
1. Define the operational concept and objectives of the app.
2. Define the requirements and scope of the app.
3. Design the architecture and user interface of the app.
4. Develop an implementation plan, breaking down the implementation into smaller tasks. the implementation plan should include a pull request for each task, merged to main branch after successful review and testing. 
5. Execute the implementation plan, coding each component of the app. 
6. Test the app thoroughly to ensure it meets the requirements and functions as expected.
