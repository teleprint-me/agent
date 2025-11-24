"""
Module: agent.hf.__main__

NOTE: This is still a Work in Progress.
"""

import click

from agent.hf.download import HuggingFaceDownload
from agent.hf.env import get_environment
from agent.hf.upload import HuggingFaceUpload


def common_options(command_func):
    decorators = [
        click.option(
            "-i",
            "--repo_id",
            prompt="Hugging Face repository ID",
            help="The Hugging Face repository ID.",
        ),
        click.option(
            "-t",
            "--repo_type",
            help="The type of repository. `model`, `dataset`, or `space`. Defaults to `None`.",
        ),
        click.option(
            "-e",
            "--env_path",
            help="The .env file path.",
        ),
        click.option(
            "-a",
            "--api_token",
            help="Hugging Face API token. Overrides configuration file.",
        ),
    ]
    for decorator in reversed(decorators):
        command_func = decorator(command_func)
    return command_func


@click.group()
def cli():
    pass


@cli.command(name="upload")
@click.option(
    "-p",
    "--local_path",
    prompt="Local path to upload",
    help="The local path from which to upload files or directories.",
)
@common_options
def upload_command(repo_id, repo_type, local_path, env_path, api_token):
    if not api_token and env_path:
        api_token = get_environment(
            file_path=env_path, variable="HUGGINGFACE_WRITE_API"
        )

    huggingface = HuggingFaceUpload(api_token)
    huggingface.upload(local_path, repo_id, repo_type)


@cli.command(name="download")
@click.option(
    "-p",
    "--local_path",
    prompt="Local path to download",
    help="The local path from which to download files or directories.",
)
@click.option(
    "-f",
    "--is_file",
    is_flag=True,
    help="Specify this flag if the local path is a file. If not set, the path is treated as a directory.",
)
@click.option(
    "-r",
    "--force_download",
    is_flag=True,
    help="Specify this flag to override resuming downloads. If not set, the download will resume from where it last stopped.",
)
@common_options
def download_command(
    repo_id,
    repo_type,
    local_path,
    force_download,
    is_file,
    env_path,
    api_token,
):
    if not api_token and env_path:
        api_token = get_environment(file_path=env_path, variable="HUGGINGFACE_READ_API")

    huggingface = HuggingFaceDownload(api_token)
    huggingface.download(local_path, repo_id, repo_type, force_download, is_file)


if __name__ == "__main__":
    cli()
