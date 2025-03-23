from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
import os
from globals import running_locally

@CrewBase
class Staff():

    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    @agent
    def researcher(self) -> Agent:
        return Agent(
            config=self.agents_config['researcher'],
            verbose=True
        )

    @agent
    def reporting_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config['reporting_analyst'],
            verbose=True
        )

    @task
    def research_task(self) -> Task:
        return Task(
            config=self.tasks_config['research_task'],
        )

    @task
    def reporting_task(self) -> Task:
        # Create results directory if it doesn't exist
        if running_locally:
            results_dir = os.path.join(os.path.dirname(__file__), 'results')
        else:
            results_dir = os.path.join('/tmp', 'results')
        os.makedirs(results_dir, exist_ok=True)
        report_path = os.path.join(results_dir, 'report.md')
        print(f"Trying to save report to: {report_path}")

        def task_function(task: Task, agent: Agent):
            # Execute the reporting task logic here
            report_content = agent.execute_task(task.description)

            # Write the report content to the output file
            with open(report_path, 'w') as f:
                f.write(report_content)
                
            if not os.path.exists(report_path):
                print(f"First attempt failed to save report to: {report_path}")
                
            return report_content

        # Create the task
        task = Task(
            config=self.tasks_config['reporting_task'],
            output_file=report_path,
            function=task_function
        )

        return task

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=False,
        )
