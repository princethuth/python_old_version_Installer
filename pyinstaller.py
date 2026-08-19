import os
import sys
import subprocess
import shutil
import glob
import time
import threading

VERSIONS = ["3.9", "3.10", "3.11", "3.12", "3.13", "3.14"]

def interactive_cleanup():
    patterns = ["py312_stub.c", "*_aarch64.deb", "pyinstaller.py.*", "old_pyinstaller.py"]
    files_to_remove = []
    for pattern in patterns:
        files_to_remove.extend(glob.glob(pattern))
    for matching_file in files_to_remove:
        if os.path.exists(matching_file):
            try:
                os.remove(matching_file)
            except Exception:
                pass

interactive_cleanup()

def show_logo():
    logo = """
 ▓█████▄  ▄▄▄       ███▄ ▄███▓ ███▄ ▄███▓ ▓██   ██▓
 ▒██▀ ██▌▒████▄    ▓██▒▀█▀ ██▒▓██▒▀█▀ ██▒  ▒██  ██▒
 ░██   █▌▒██  ▀█▄  ▓██    ▓██░▓██    ▓██░   ▒██ ██░
 ░▓█▄   ▌░██▄▄▄▄██ ▒██    ▒██ ▒██    ▒██    ░ ▐██▓░
 ░▒████▓  ▓█   ▓██▒▒██▒   ░██▒▒██▒   ░██▒   ░ ██▒▓░
  ▒▒▓  ▒  ▒▒   ▓▒█░░ ▒░   ░  ░░ ▒░   ░  ░    ██▒▒▒ 
  ░ ▒  ▒   ▒   ▒▒ ░░  ░      ░░  ░      ░  ▓██ ░▒░ 
  ░ ░  ░   ░   ▒   ░      ░   ░      ░     ▒ ▒ ░░  
    ░          ░  ░       ░          ░     ░ ░     
  ░                                        ░ ░     
    """
    print(logo)

def run_progress_bar(message, stop_event):
    percent = 0
    while percent <= 100 and not stop_event.is_set():
        sys.stdout.write(f"\r{message}: [{"#" * (percent // 4):<25}] {percent}%")
        sys.stdout.flush()
        time.sleep(0.05)
        if percent < 99:
            percent += 1
    sys.stdout.write(f"\r{message}: [{"#" * 25}] 100%\n")
    sys.stdout.flush()

def run_cmd_with_bar(cmd, message, transparent=False):
    stop_flag = threading.Event()
    bar_thread = threading.Thread(target=run_progress_bar, args=(message, stop_flag))
    
    if not transparent:
        bar_thread.start()
        
    try:
        stdout_dest = None if transparent else subprocess.DEVNULL
        stderr_dest = None if transparent else subprocess.DEVNULL
        subprocess.run(cmd, shell=True, check=True, stdout=stdout_dest, stderr=stderr_dest)
        success = True
    except subprocess.CalledProcessError:
        success = False
        
    if not transparent:
        stop_flag.set()
        bar_thread.join()
    return success

def check_version_status(cmd_name):
    if shutil.which(cmd_name):
        try:
            res = subprocess.run(f"{cmd_name} -V", shell=True, capture_output=True, text=True)
            return res.stdout.strip()
        except Exception:
            return "Installed"
    return None

def show_installed_versions():
    print("\n=====================================")
    print("      CHECKING INSTALLED STATUS      ")
    print("=====================================")
    default_py = check_version_status("python3")
    if default_py:
        print(f"[+] System Release: {default_py}")
    print("-------------------------------------")
    for v in VERSIONS:
        status = check_version_status(f"python{v}")
        if status:
            print(f"[+] Python {v:<7} : Installed ({status})")
        else:
            print(f"[-] Python {v:<7} : Not Installed")
    print("=====================================")
    input("\nPress Enter to return to main menu...")

def install_version(version):
    print(f"\n[*] Initializing setup for Python {version}...")
    
    # 1. Primary Attempt: Standard Repository Method
    run_cmd_with_bar("pkg install tur-repo -y && pkg update -y", "[*] Syncing System Repositories")
    
    package_target = "python" if version == "3.14" else f"python{version}"
    cmd = f"pkg install {package_target} -y"
    
    success = run_cmd_with_bar(cmd, f"[+] Method 1: Fetching via Package Manager")
    
    # 2. Automated Fallback: GitHub Main Host Direct Download Method
    if not success and version in ["3.12", "3.13"]:
        print(f"\n[!] Method 1 failed (Package missing on mirror index).")
        print(f"[*] Switching to Method 2: Pulling directly from GitHub main host binaries...")
        
        # Exact verified build files URLs from the stable TUR releases tree
        urls = {
            "3.12": "https://github.com/termux-user-repository/tur/releases/download/packages/python312_3.12.3_aarch64.deb",
            "3.13": "https://github.com/termux-user-repository/tur/releases/download/packages/python313_3.13.1_aarch64.deb"
        }
        
        deb_file = f"python{version.replace('.', '')}_aarch64.deb"
        download_cmd = f"curl -L -o {deb_file} {urls[version]}"
        install_fallback_cmd = f"dpkg -i {deb_file} && rm -f {deb_file}"
        
        # Run fallback functions visually
        dl_success = run_cmd_with_bar(download_cmd, f"[+] Downloading pre-compiled binaries from Main Host")
        if dl_success:
            success = run_cmd_with_bar(install_fallback_cmd, f"[+] Unpacking local structures into $PREFIX/bin")
            
    if success:
        print(f"\n[✔] Success! Python {version} is natively functional via system path configuration.")
    else:
        print(f"\n[!] Critical: Both mirror index search and Main Host deployment pipelines failed.")

def uninstall_version(version, auto_confirm=False):
    if not auto_confirm:
        confirm = input(f"\n[?] Confirm complete removal of Python {version}? (y/n): ").strip().lower()
        if confirm != 'y':
            return False

    package_target = "python" if version == "3.14" else f"python{version}"
    cmd = f"pkg remove {package_target} -y"
    return run_cmd_with_bar(cmd, f"[-] Removing Python {version}")

def submenu(action):
    while True:
        print(f"\n--- SELECT VERSION TO {action.upper()} ---")
        for i, v in enumerate(VERSIONS, 1):
            print(f"{i}. Python {v}")
        print(f"{len(VERSIONS)+1}. Cancel (Go Back)")
        
        choice = input("\nChoose an option: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(VERSIONS):
            v = VERSIONS[int(choice) - 1]
            install_version(v) if action == "install" else uninstall_version(v)
            break
        elif choice == str(len(VERSIONS)+1):
            break

def main():
    while True:
        show_logo()
        print("=====================================")
        print("    AUTONOMOUS NATIVE MANAGER        ")
        print("=====================================")
        print("1. Select py version to install.")
        print("2. Select py version to uninstall.")
        print("3. Install all available version from 3.9 to latest version.")
        print("4. Uninstall all available version except the latest one.")
        print("5. Show all installed versions of python.")
        print("6. Exit.")
        
        choice = input("\nChoose an option (1-6): ").strip()
        if choice == "1":
            submenu("install")
        elif choice == "2":
            submenu("uninstall")
        elif choice == "3":
            print("\n[*] Initializing bulk deployment loop...")
            for v in VERSIONS:
                install_version(v)
            print("\n[✔] Bulk operation sequence complete.")
            input("\nPress Enter to continue...")
        elif choice == "4":
            confirm_bulk = input("\n[?] Execute bulk uninstallation sequence? (y/n): ").strip().lower()
            if confirm_bulk == 'y':
                for v in VERSIONS[:-1]: 
                    uninstall_version(v, auto_confirm=True)
                print("\n[✔] Cleanup completed.")
            input("\nPress Enter to continue...")
        elif choice == "5":
            show_installed_versions()
        elif choice == "6":
            sys.exit(0)

if __name__ == "__main__":
    main()
