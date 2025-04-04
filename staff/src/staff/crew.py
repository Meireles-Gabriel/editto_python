from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from globals import running_locally

# Staff class organizes AI agents and their tasks for magazine creation
# Classe Staff organiza agentes de IA e suas tarefas para criação de revistas
@CrewBase
class Staff():
    # Configuration file paths for agents and tasks
    # Caminhos dos arquivos de configuração para agentes e tarefas
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    # Content Rewriter Agent - Rewrites news articles in magazine style
    # Agente Reescritor de Conteúdo - Reescreve artigos de notícias no estilo de revista
    @agent
    def content_rewriter(self) -> Agent:
        """
        Creates the content rewriter agent that transforms news articles into magazine-style content.
        Cria o agente reescritor de conteúdo que transforma artigos de notícias em conteúdo estilo revista.
        """
        return Agent(
            config=self.agents_config['content_rewriter'],
            verbose=False
        )

    # Cover Designer Agent - Creates magazine cover content
    # Agente Designer de Capa - Cria conteúdo para a capa da revista
    @agent
    def cover_designer(self) -> Agent:
        """
        Creates the cover designer agent that develops titles, subtitles, and highlights for the magazine cover.
        Cria o agente designer de capa que desenvolve títulos, subtítulos e destaques para a capa da revista.
        """
        return Agent(
            config=self.agents_config['cover_designer'],
            verbose=False
        )

    # Task to rewrite news articles into magazine format
    # Tarefa para reescrever artigos de notícias em formato de revista
    @task
    def rewrite_articles_task(self) -> Task:
        """
        Creates a task for rewriting news articles in magazine style.
        Cria uma tarefa para reescrever artigos de notícias no estilo de revista.
        """
        return Task(
            config=self.tasks_config['rewrite_articles_task'],
        )

    # Task to create magazine cover content
    # Tarefa para criar conteúdo da capa da revista
    @task
    def create_cover_content_task(self) -> Task:
        """
        Creates a task for generating magazine cover content.
        Cria uma tarefa para gerar conteúdo da capa da revista.
        """
        return Task(
            config=self.tasks_config['create_cover_content_task'],
        )

    # Content Crew - Group of agents and tasks for article rewriting
    # Equipe de Conteúdo - Grupo de agentes e tarefas para reescrita de artigos
    @crew
    def content_crew(self) -> Crew:
        """
        Assembles a crew with content rewriter agent and article rewriting task.
        Monta uma equipe com o agente reescritor de conteúdo e a tarefa de reescrita de artigos.
        """
        if running_locally:
            print("Initializing content crew.")  # Debug print
        return Crew(
            agents=[self.content_rewriter()],
            tasks=[self.rewrite_articles_task()],
            process=Process.sequential,  # Tasks run in sequence / Tarefas executadas em sequência
            verbose=False,
        )

    # Design Crew - Group of agents and tasks for cover creation
    # Equipe de Design - Grupo de agentes e tarefas para criação da capa
    @crew
    def design_crew(self) -> Crew:
        """
        Assembles a crew with cover designer agent and cover content creation task.
        Monta uma equipe com o agente designer de capa e a tarefa de criação de conteúdo da capa.
        """
        if running_locally:
            print("Initializing design crew.")  # Debug print
        return Crew(
            agents=[self.cover_designer()],
            tasks=[self.create_cover_content_task()],
            process=Process.sequential,  # Tasks run in sequence / Tarefas executadas em sequência
            verbose=False,
        )