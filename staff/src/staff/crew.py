from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

@CrewBase
class Staff():
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    @agent
    def content_rewriter(self) -> Agent:
        print("Initializing content rewriter agent.")  # Debug print
        return Agent(
            config=self.agents_config['content_rewriter'],
            verbose=True
        )

    @agent
    def cover_designer(self) -> Agent:
        print("Initializing cover designer agent.")  # Debug print
        return Agent(
            config=self.agents_config['cover_designer'],
            verbose=True
        )

    @task
    def rewrite_articles_task(self) -> Task:
        print("Creating rewrite articles task.")  # Debug print
        return Task(
            config=self.tasks_config['rewrite_articles_task'],
        )

    @task
    def create_cover_content_task(self) -> Task:
        print("Creating cover content task.")  # Debug print
        return Task(
            config=self.tasks_config['create_cover_content_task'],
        )

    @crew
    def crew(self) -> Crew:
        print("Initializing crew with agents and tasks.")  # Debug print
        return Crew(
            agents=[self.content_rewriter(), self.cover_designer()],
            tasks=[self.rewrite_articles_task(), self.create_cover_content_task()],
            process=Process.sequential,
            verbose=True,
        )