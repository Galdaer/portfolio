#!/bin/bash
# External Drive Setup Script for 4TB Medical Data Storage
# Sets up external drive at /home/intelluxe/database/ for complete medical archives

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
MOUNT_POINT="/home/intelluxe/database"
DEVICE="/dev/sda"  # 4TB external drive detected from lsblk
FILESYSTEM="ext4"

print_section() {
    echo -e "\n${BLUE}=== $1 ===${NC}\n"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

detect_external_drives() {
    print_section "Detecting External Drives"
    
    echo "Available block devices:"
    lsblk -o NAME,SIZE,TYPE,MOUNTPOINT | grep -E "(disk|part)"
    
    echo -e "\nUSB devices:"
    lsusb | grep -i "mass storage\|external\|disk" || echo "No USB storage devices detected"
    
    echo -e "\nDisk information:"
    sudo fdisk -l | grep -E "Disk /dev/[a-z]+:|GB|TB" || true
}

check_drive_capacity() {
    local device=$1
    local size_info=$(sudo fdisk -l "$device" | grep "Disk $device" | awk '{print $3 " " $4}' | sed 's/,//')
    local size_value=$(echo "$size_info" | awk '{print $1}')
    local size_unit=$(echo "$size_info" | awk '{print $2}')
    
    echo "Drive size: $size_value $size_unit"
    
    # Convert to GB for comparison
    local size_gb=0
    if [[ "$size_unit" == "TiB" ]]; then
        size_gb=$(echo "$size_value * 1024" | bc -l | cut -d. -f1)
    elif [[ "$size_unit" == "GiB" ]]; then
        size_gb=$(echo "$size_value" | cut -d. -f1)
    elif [[ "$size_unit" == "TB" ]]; then
        size_gb=$(echo "$size_value * 1000" | bc -l | cut -d. -f1)
    elif [[ "$size_unit" == "GB" ]]; then
        size_gb=$(echo "$size_value" | cut -d. -f1)
    fi
    
    if [[ $size_gb -ge 3000 ]]; then
        print_success "Drive capacity: ${size_gb}GB (sufficient for ~242GB medical data)"
        return 0
    else
        print_error "Drive capacity: ${size_gb}GB (insufficient for ~242GB medical data)"
        return 1
    fi
}

format_drive() {
    local device=$1
    
    print_section "Formatting External Drive"
    
    print_warning "WARNING: This will ERASE ALL DATA on $device"
    echo "Are you sure you want to format $device? (type 'YES' to confirm)"
    read -r confirmation
    
    if [[ "$confirmation" != "YES" ]]; then
        print_error "Drive formatting cancelled"
        exit 1
    fi
    
    # Unmount any mounted partitions on this device
    print_section "Unmounting Device Partitions"
    for partition in $(lsblk -np "$device" | awk 'NR>1 {print $1}'); do
        if mountpoint=$(lsblk -no MOUNTPOINT "$partition" | grep -v '^$'); then
            print_warning "Unmounting $partition from $mountpoint"
            sudo umount "$partition" || true
        fi
    done
    
    # Create partition table
    print_section "Creating Partition Table"
    sudo parted "$device" mklabel gpt
    
    # Create single partition using entire disk
    sudo parted "$device" mkpart primary ext4 0% 100%
    
    # Get partition device (usually ${device}1)
    local partition="${device}1"
    
    # Format with ext4
    print_section "Formatting with ext4 filesystem"
    sudo mkfs.ext4 -F "$partition" -L "medical_data"
    
    print_success "Drive formatted successfully: $partition"
    DEVICE="$partition"
}

setup_mount_point() {
    print_section "Setting Up Mount Point"
    
    # Create mount directory
    sudo mkdir -p "$MOUNT_POINT"
    print_success "Created mount directory: $MOUNT_POINT"
    
    # Get UUID of the formatted partition
    local uuid=$(sudo blkid "$DEVICE" | grep -o 'UUID="[^"]*"' | cut -d'"' -f2)
    
    if [[ -z "$uuid" ]]; then
        print_error "Could not get UUID for $DEVICE"
        exit 1
    fi
    
    print_success "Device UUID: $uuid"
    
    # Add to /etc/fstab for automatic mounting
    print_section "Configuring Automatic Mount"
    
    # Check if entry already exists
    if grep -q "$MOUNT_POINT" /etc/fstab; then
        print_warning "Mount entry already exists in /etc/fstab"
        sudo sed -i "\|$MOUNT_POINT|d" /etc/fstab
        print_success "Removed existing entry"
    fi
    
    # Add new entry
    echo "UUID=$uuid $MOUNT_POINT ext4 defaults,nofail,user,exec 0 2" | sudo tee -a /etc/fstab
    print_success "Added mount entry to /etc/fstab"
    
    # Test mount
    sudo mount -a
    print_success "Mounted drive at $MOUNT_POINT"
    
    # Set ownership to current user
    sudo chown -R $(whoami):$(whoami) "$MOUNT_POINT"
    print_success "Set ownership to $(whoami)"
}

create_directory_structure() {
    print_section "Creating Medical Data Directory Structure"
    
    local dirs=(
        "medical_complete"
        "medical_complete/pubmed_complete"
        "medical_complete/pubmed_complete/baseline"
        "medical_complete/pubmed_complete/updates"
        "medical_complete/clinicaltrials_complete"
        "medical_complete/fda_complete"
        "medical_complete/fda_complete/drug_labels"
        "medical_complete/fda_complete/orange_book"
        "medical_complete/fda_complete/ndc_directory"
        "medical_complete/fda_complete/drugs_fda"
        "postgresql_data"
        "medical_mirrors_data"
        "backups"
        "logs"
    )
    
    for dir in "${dirs[@]}"; do
        mkdir -p "$MOUNT_POINT/$dir"
        print_success "Created: $MOUNT_POINT/$dir"
    done
}

test_drive_performance() {
    print_section "Testing Drive Performance"
    
    # Test write speed
    echo "Testing write performance..."
    local write_speed=$(dd if=/dev/zero of="$MOUNT_POINT/test_write" bs=1M count=1000 2>&1 | grep -o '[0-9.]* MB/s' | tail -1)
    rm -f "$MOUNT_POINT/test_write"
    print_success "Write speed: $write_speed"
    
    # Test read speed  
    echo "Testing read performance..."
    dd if=/dev/zero of="$MOUNT_POINT/test_read" bs=1M count=1000 > /dev/null 2>&1
    local read_speed=$(dd if="$MOUNT_POINT/test_read" of=/dev/null bs=1M 2>&1 | grep -o '[0-9.]* MB/s' | tail -1)
    rm -f "$MOUNT_POINT/test_read"
    print_success "Read speed: $read_speed"
    
    # Check available space
    local available=$(df -h "$MOUNT_POINT" | awk 'NR==2{print $4}')
    print_success "Available space: $available"
}

main() {
    print_section "External Drive Setup for Medical Data"
    echo "This script will set up a 4TB external drive for complete medical archives"
    echo "Mount point: $MOUNT_POINT"
    echo "Estimated data size: ~242GB"
    
    # Check if running as root or with sudo access
    if [[ $EUID -eq 0 ]] || sudo -n true 2>/dev/null; then
        print_success "Running with required privileges"
    else
        print_error "This script requires sudo access. Please run with sudo or ensure sudo is available."
        exit 1
    fi
    
    # Detect available drives
    detect_external_drives
    
    # Use the pre-configured device (4TB drive detected from lsblk)
    device_input="$DEVICE"
    print_success "Using detected 4TB external drive: $device_input"
    
    if [[ ! -b "$device_input" ]]; then
        print_error "Device $device_input does not exist or is not a block device"
        exit 1
    fi
    
    # Check drive capacity
    if ! check_drive_capacity "$device_input"; then
        exit 1
    fi
    
    # Format the drive
    format_drive "$device_input"
    
    # Setup mount point and fstab
    setup_mount_point
    
    # Create directory structure
    create_directory_structure
    
    # Test performance
    test_drive_performance
    
    print_section "Setup Complete"
    print_success "External drive successfully set up at $MOUNT_POINT"
    print_success "Directory structure created for medical data"
    print_success "Drive will automatically mount on boot"
    
    echo -e "\n${BLUE}Next Steps:${NC}"
    echo "1. Run the migration script to move existing data:"
    echo "   bash /home/intelluxe/scripts/migrate_medical_data.sh"
    echo ""
    echo "2. Start the full medical archives download:"
    echo "   python3 /home/intelluxe/scripts/download_full_medical_archives.py --data-dir $MOUNT_POINT/medical_complete"
    echo ""
    echo "3. Update VS Code settings for the new drive location"
}

# Handle interrupts
trap 'print_error "Setup interrupted"; exit 1' INT TERM

# Run main function
main "$@"
