from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

@CrewBase
class Staff():
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    @agent
    def content_rewriter(self) -> Agent:
        return Agent(
            config=self.agents_config['content_rewriter'],
            verbose=False
        )

    @agent
    def cover_designer(self) -> Agent:
        return Agent(
            config=self.agents_config['cover_designer'],
            verbose=False
        )

    @task
    def rewrite_articles_task(self) -> Task:
        return Task(
            config=self.tasks_config['rewrite_articles_task'],
        )

    @task
    def create_cover_content_task(self) -> Task:
        return Task(
            config=self.tasks_config['create_cover_content_task'],
        )

    @crew
    def content_crew(self) -> Crew:
        print("Initializing content crew.")  # Debug print
        return Crew(
            agents=[self.content_rewriter()],
            tasks=[self.rewrite_articles_task()],
            process=Process.sequential,
            verbose=False,
        )

    @crew
    def design_crew(self) -> Crew:
        print("Initializing design crew.")  # Debug print
        return Crew(
            agents=[self.cover_designer()],
            tasks=[self.create_cover_content_task()],
            process=Process.sequential,
            verbose=False,
        )