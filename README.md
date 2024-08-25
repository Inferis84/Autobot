# Autobot
Discord bot for pulling images from selected channels and saving them locally.

## About Autobot
This bot will monitor a server for images. It's restricted to a specified role to prevent abuse by regular users. This role can be changed at the top of the script, which will be used by all commands.

Before any images are saved, channels need to be tracked. This can be done using the `$track` command, either by specifying which channel to track with `$track channelname`, or by just calling the `$track` command in the channel you want to track.

To get a list of what channels are currently tracked, use the `$list` command.

If you want to remove a channel from being tracked, the `$untrack` command can be used. This works in the same way as the `$track` command.

Once a channel is tracked, new messages will be monitored for images, and they will be saved to a local directory. At the top of the script, the `imagepath` variable can be adjusted to point to where images should be saved. In this folder, images will be organized by week, starting on Sunday, and then by channel name, user name, and finally the images will be named with an index based on the number of images already saved in that folder. This organization is designed to make it easy for using these saved images on a weekly basis.

If you want to have all of the original pictures in a channel saved as well, the `$scan` command will look back through all the message history in each tracked channel, and save all images found. It will use the same organization as above. The first time running this command will be very slow, as it's doing a lot of work. Once complete, all messages that have been processed are saved to a local database, so running `$scan` again won't pull the same images a second time. This will speed the process up immensely, and should only be required when tracking new channels, or if the bot goes down and you want to catch up whatever's been missed.

## Initial setup
The .envsetup file will need to be renamed to .env for the connection to Discord to work. You will also need to change the <token> value to your Discord bot's token, generated on your bot's configuration area in the [Discord Developer Portal](https://discord.com/developers/applications).

## Docker
This project has a docker image available to run as a docker container. The image is on [Dockerhub](https://hub.docker.com/repository/docker/inferis84/autobot/general), or a new one can be built with the included dockerfile.

When running a container, make sure to mount the /images and /db folders so that data is not lost with a container. Also, the environment variable `DISCORD_TOKEN` is also required, which should be set to your bot's token as you would in the `.env` file.