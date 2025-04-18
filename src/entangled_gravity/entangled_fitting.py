"""
entangled_fitting.py

Script that scans the local folder for SPARC-like .dat files,
prompts user to pick one,
fits the entanglement-based velocity model to the observed rotation curve,
and saves a CSV + figure of the results, including residuals.

Usage: 
    python entangled_fitting.py
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

####################################
# 1) Model Definitions
####################################

def v_ent(r, kappa, r0, alpha):
    S0 = 1.0
    with np.errstate(invalid='ignore', divide='ignore'):
        dS_dr = -alpha * S0 / r0 * np.power((1.0 + r / r0), -(alpha + 1))
    v_sq = r * np.abs(kappa * dS_dr)
    return np.sqrt(np.maximum(v_sq, 0.0))

def v_total(r, kappa, r0, alpha, vbar):
    return np.sqrt(vbar**2 + v_ent(r, kappa, r0, alpha)**2)

####################################
# 2) Main Execution
####################################

def main():
    folder = os.getcwd()
    dat_files = [f for f in os.listdir(folder) if f.endswith('.dat')]
    if not dat_files:
        print("No .dat files found in current folder. Exiting.")
        sys.exit(0)

    print("Found the following .dat files in this folder:")
    for i, fname in enumerate(dat_files):
        print(f"  [{i}] {fname}")

    try:
        choice = int(input(f"\nEnter the index of the file you want to load [0..{len(dat_files)-1}]: "))
    except ValueError:
        print("Invalid input. Exiting.")
        sys.exit(0)

    if choice < 0 or choice >= len(dat_files):
        print("Choice out of range. Exiting.")
        sys.exit(0)

    chosen_file = dat_files[choice]
    print(f"\nYou selected: {chosen_file}\n")

    # Load data
    col_names = ['r_kpc','V_obs','V_err','V_gas','V_disk','V_bul','SB_disk','SB_bul']
    df = pd.read_csv(chosen_file, comment='#', delim_whitespace=True, names=col_names)

    print("Preview of loaded data:")
    print(df.head(), "\n")

    r_vals    = df['r_kpc'].values
    V_obs     = df['V_obs'].values
    V_err     = df['V_err'].values
    V_gas     = df['V_gas'].values
    V_disk    = df['V_disk'].values
    V_bul     = df['V_bul'].values

    V_baryon  = np.sqrt(V_gas**2 + V_disk**2 + V_bul**2)

    def model(r, kappa, r0, alpha):
        return v_total(r, kappa, r0, alpha, V_baryon)

    param_bounds = ([0, 0.01, 0.01], [1e4, 1e3, 20])
    p0 = [10.0, 2.0, 1.0]

    try:
        popt, pcov = curve_fit(
            model, r_vals, V_obs,
            sigma=V_err,
            p0=p0,
            bounds=param_bounds,
            maxfev=5000
        )
    except RuntimeError as e:
        print(f"Fitting error: {e}")
        sys.exit(0)

    kappa_fit, r0_fit, alpha_fit = popt
    print("Best-fit parameters:")
    print(f"  kappa = {kappa_fit:.4g}")
    print(f"  r0    = {r0_fit:.4g} kpc")
    print(f"  alpha = {alpha_fit:.4g}")

    V_fit = model(r_vals, *popt)
    V_ent_ = v_ent(r_vals, kappa_fit, r0_fit, alpha_fit)

    residuals = V_obs - V_fit
    rmse = np.sqrt(np.mean(residuals**2))
    print(f"Root-mean-square error (RMSE): {rmse:.2f} km/s")

    # Save CSV
    out_csv = chosen_file.replace('.dat','_entfit.csv')
    df_out = pd.DataFrame({
        'r_kpc' : r_vals,
        'V_obs' : V_obs,
        'V_err' : V_err,
        'V_gas' : V_gas,
        'V_disk': V_disk,
        'V_bulge':V_bul,
        'V_baryon': V_baryon,
        'V_ent': V_ent_,
        'V_total': V_fit,
        'residual': residuals
    })
    df_out.to_csv(out_csv, index=False)
    print(f"Saved fit results to: {out_csv}")

    # Plot with residuals
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 8), sharex=True,
                                   gridspec_kw={'height_ratios': [3, 1]})

    ax1.errorbar(r_vals, V_obs, yerr=V_err, fmt='o', color='k', label='Observed $V_{obs}$')
    ax1.plot(r_vals, V_baryon, '--', color='gray', label='$V_{baryon}$')
    ax1.plot(r_vals, V_ent_, '-', color='blue', label='$V_{ent}$')
    ax1.plot(r_vals, V_fit, '-', color='red', label='Total $V_{fit}$')
    ax1.set_ylabel("Velocity [km/s]")
    ax1.set_title(f"Rotation Curve Fit: {chosen_file}\n(kappa={kappa_fit:.2f}, r0={r0_fit:.2f}, alpha={alpha_fit:.2f}, RMSE={rmse:.2f})")
    ax1.grid(True)
    ax1.legend()

    ax2.axhline(0, color='gray', linestyle='--')
    ax2.errorbar(r_vals, residuals, yerr=V_err, fmt='o', color='darkred', markersize=4)
    ax2.set_xlabel("Radius [kpc]")
    ax2.set_ylabel("Residual")
    ax2.grid(True)

    plt.tight_layout()
    out_fig = chosen_file.replace('.dat','_entfit_with_residuals.png')
    plt.savefig(out_fig, dpi=150)
    print(f"Saved figure to: {out_fig}")

    plt.show()

if __name__ == "__main__":
    main()
