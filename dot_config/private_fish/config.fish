if status is-interactive
    # Commands to run in interactive sessions can go here

    set PATH /opt/homebrew/bin $PATH # <-追加
    set -x N_PREFIX $HOME/.n.
    set N_PREFIX $HOME/.n
    set -x PATH /Users/himihiromu/.n/bin $PATH
    set -x DOCKER_HOST unix://$HOME/.lima/docker/sock/docker.sock
    set -x PATH $HOME/.cargo/bin $PATH
    set -x ANDROID_HOME /usr/local/share/android-sdk
    set -x PATH $ANDROID_HOME/tools/bin $PATH
    set -x PATH $ANDROID_HOME/platform-tools $PATH
end

# Created by `pipx` on 2024-09-30 16:43:47
set PATH $PATH /Users/himihiromu/.local/bin