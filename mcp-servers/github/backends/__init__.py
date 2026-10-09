import os


def get_backend():
    github_mode = os.getenv("GITHUB_MODE", "").lower()
    if github_mode == "demo":
        from .simulated import SimulatedGitHubBackend

        return SimulatedGitHubBackend()
    if github_mode == "live":
        from .live import LiveGitHubBackend

        return LiveGitHubBackend()

    cloudops_mode = os.getenv("CLOUDOPS_MODE", "demo").lower()
    if (cloudops_mode == "live" or os.getenv("GITHUB_TOKEN")) and os.getenv("GITHUB_TOKEN"):
        from .live import LiveGitHubBackend

        return LiveGitHubBackend()
    from .simulated import SimulatedGitHubBackend

    return SimulatedGitHubBackend()
