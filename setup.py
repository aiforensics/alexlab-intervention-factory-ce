from setuptools import setup


setup(
    name="alexlab_if",
    license='GPLv3',
    packages=['alexlab_if', 'alexlab_if.stopwords'],
    description='Processes templates and arguments to generate user actions at scale (i.e. prompts for chatbot platforms such as Copilot and Gemini or search queries for TikTok and Youtube). ',
    author='AI Forensics',
    author_email='info@aiforensics.org',
    package_dir={'alexlab_if': 'alexlab_if'},
    package_data={'alexlab_if': ['stopwords/*.txt']},
)
