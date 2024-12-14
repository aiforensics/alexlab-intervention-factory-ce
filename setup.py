from setuptools import setup


setup(
    name="alexlab_user_actions",
    license='GPLv3',
    packages=['alexlab_user_actions', 'alexlab_user_actions.stopwords'],
    description='Processes templates and arguments to generate user actions at scale (i.e. prompts for chatbot platforms such as Copilot and Gemini or search queries for TikTok and Youtube). ',
    author='AI Forensics',
    author_email='info@aiforensics.org',
    package_dir={'alexlab_user_actions': 'alexlab_user_actions'},
    package_data={'alexlab_user_actions': ['stopwords/*.txt']},
)
