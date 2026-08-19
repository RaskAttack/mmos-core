# Use the official Arch Linux base image
FROM archlinux:latest

# Install archiso, git, and the reflector tool
RUN pacman -Sy --noconfirm archlinux-keyring && \
    pacman -Syu --noconfirm archiso make git reflector

# Use reflector to find the 10 fastest, most recently synced mirrors and save them
RUN reflector --latest 10 --sort rate --save /etc/pacman.d/mirrorlist

# Set the working directory inside the container
WORKDIR /mmos-build

# Build the ISO
CMD mkarchiso -v -w /tmp/work -o /mmos-build/out /mmos-build/arch-profile
