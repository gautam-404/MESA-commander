import subprocess
import shlex
import sys, os
import shutil
from rich import print

from ..MesaFileHandler.support import *


def check_exists(exists, projName):
        """Checks if the project exists."""
        if not exists:
            raise FileNotFoundError(f"Project '{projName}' does not exist. Please create it first.")


def run_subprocess(commands, dir, silent=True, runlog='', status=None, 
                    gyre=False, filename="", data_format="FGONG", parallel=False, gyre_in="gyre.in"):
    """Runs a subprocess.

    Args:
        commands (str or list): Command to be run.
        dir (str): Directory in which the command is to be run.
        silent (bool, optional): Run the command silently. Defaults to False.
        runlog (str, optional): Log file to write the output to. Defaults to ''.
        status (rich.status.Status, optional): Status to update. Defaults to status.Status("Running...").
        gyre (bool, optional): Whether the command is a gyre command. Defaults to False.
        filename (str, optional): The name of the file to be used by gyre. Defaults to None.
        data_format (str, optional): The format of the data to be used by gyre. Defaults to None.

    Returns:
        bool: True if the command ran successfully, False otherwise.
    """      
    if gyre:
        if parallel:
            num = filename.split(".")[0]
            shutil.copy(gyre_in, os.path.join(dir, f"gyre{num}.in"))
            gyre_in = os.path.join(dir, f"gyre{num}.in")
            commands = commands.replace("gyre.in", f"gyre{num}.in")
        modify_gyre_params(dir, filename, data_format, gyre_in=gyre_in) 

    evo_terminated = False
    with subprocess.Popen(shlex.split(commands), bufsize=0, cwd=dir,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True) as proc:
        with open(runlog, "a+") as logfile:
            for outline in proc.stdout:
                logfile.write(outline)
                logfile.flush()
                if silent is False:
                    sys.stdout.write(outline)
                elif not gyre:
                    if "terminated evolution:" in outline:
                        evo_terminated = True
                    age = process_outline(outline)
                    if age is not None:
                        if age < 1/365:
                            age_str = f"[b]Age: [cyan]{age*365*24:.4f}[/cyan] hours"
                        elif 1/365 < age < 1:
                            age_str = f"[b]Age: [cyan]{age*365:.4f}[/cyan] days"
                        elif 1 < age < 1000:
                            age_str = f"[b]Age: [cyan]{age:.3f}[/cyan] years"
                        else:
                            age_str = f"[b]Age: [cyan]{age:.3e}[/cyan] years"
                        if parallel is False:
                            status.update(status=f"[b i cyan3]Running....[/b i cyan3]\n"+age_str, spinner="moon")
            for errline in proc.stderr:
                logfile.write(errline)
                sys.stdout.write(errline)
            logfile.write( "\n\n"+("*"*100)+"\n\n" )

        _data, error = proc.communicate()
    if gyre and parallel:
        with open('gyre.log', 'a+') as f:
            f.write(f"Done with {filename}.")
        os.remove(gyre_in)
    if proc.returncode or error:
        print('The process raised an error:', proc.returncode, error)
        return False
    elif evo_terminated:
        return False
    else:
        return True

def process_outline(outline):
    try:
        keyword1 = outline.split()[-1]
        keyword2 = outline.split()[-2] + " " + outline.split()[-1]
        keyword3 = outline.split()[-3] + " " + outline.split()[-2] + " " + outline.split()[-1]
        if keyword1 in dt_limit_values or keyword2 in dt_limit_values or keyword3 in dt_limit_values:
            return float(outline.split()[0])
        else:
            return None
    except:
        return None


def writetoGyreFile(dir, parameter, value, default_section, gyre_in="gyre.in"):
    """Writes the parameter and its value to the inlist file.

    Args:
        filename (str): The path to the inlist file.
        parameter (str): The parameter to be written.
        value (str): The value of the parameter to be written.
        inlistDict (dict): A dictionary with all the parameters and their values.
        defaultsDict (dict): A dictionary with all the parameters and their values.
        sections (list): A list with the sections of the inlist file.
    """    
    this_section = False
    with cd(dir):
        with open(gyre_in, "r") as file:
            lines = file.readlines()
        with open(gyre_in, "w+") as f:
            indent = "    "
            for line in lines:
                edited = False
                if default_section in line:
                    this_section = True
                if this_section:
                    if parameter in line:
                        f.write(line.replace(line.split("=")[1], f" {value}    ! Changed\n"))
                        edited = True
                        this_section = False
                    elif line[0] == "/":
                        f.write(indent)
                        f.write(f"{parameter} = {value}    ! Added\n")
                        f.write("/")
                        edited = True
                        this_section = False
                if not edited:
                    f.write(line)

   

def modify_gyre_params(LOGS_dir, filename, data_format, gyre_in="gyre.in"):
    if data_format == "GYRE":
        file_format = "MESA"
    elif data_format == "FGONG":
        file_format = "FGONG"
    writetoGyreFile(LOGS_dir, parameter="model_type", value="'EVOL'", default_section="&model", gyre_in=gyre_in)
    writetoGyreFile(LOGS_dir, parameter="file_format", value=f"'{file_format}'", default_section="&model", gyre_in=gyre_in)
    writetoGyreFile(LOGS_dir, parameter="file", value=f"'{filename}'", default_section="&model", gyre_in=gyre_in)
    writetoGyreFile(LOGS_dir, parameter="summary_file", value=f"'{filename.split('.')[0]}-freqs.dat'", default_section="&ad_output", gyre_in=gyre_in)
    writetoGyreFile(LOGS_dir, parameter="summary_file", value="'freq_output_nonad.txt'", default_section="&nad_output", gyre_in=gyre_in)

dt_limit_values = ['burn steps', 'Lnuc', 'Lnuc_cat', 'Lnuc_H', 'Lnuc_He', 'lgL_power_phot', 'Lnuc_z', 'bad_X_sum',
                  'dH', 'dH/H', 'dHe', 'dHe/He', 'dHe3', 'dHe3/He3', 'dL/L', 'dX', 'dX/X', 'dX_nuc_drop', 'delta mdot',
                  'delta total J', 'delta_HR', 'delta_mstar', 'diff iters', 'diff steps', 'min_dr_div_cs', 'dt_collapse',
                  'eps_nuc_cntr', 'error rate', 'highT del Ye', 'hold', 'lgL', 'lgP', 'lgP_cntr', 'lgR', 'lgRho', 'lgRho_cntr',
                  'lgT', 'lgT_cntr', 'lgT_max', 'lgT_max_hi_T', 'lgTeff', 'dX_div_X_cntr', 'lg_XC_cntr', 'lg_XH_cntr', 
                  'lg_XHe_cntr', 'lg_XNe_cntr', 'lg_XO_cntr', 'lg_XSi_cntr', 'XC_cntr', 'XH_cntr', 'XHe_cntr', 'XNe_cntr',
                  'XO_cntr', 'XSi_cntr', 'log_eps_nuc', 'max_dt', 'neg_mass_frac', 'adjust_J_q', 'solver iters', 'rel_E_err',
                  'varcontrol', 'max increase', 'max decrease', 'retry', 'b_****']