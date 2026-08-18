# Use the official Arch Linux base image
FROM archlinux:latest

# Update system and install the tools needed to build the ISO
RUN pacman -Syu --noconfirm && \
    pacman -S --noconfirm archiso make git

# Set the working directory inside the container
WORKDIR /mmos-build

# When the container runs, build the ISO using the mounted profile,
# and output it to the /mmos-build/out directory
CMD mkarchiso -v -w /tmp/work -o /mmos-build/out /mmos-build/arch-profile
