use std::fs::{self, File};
use std::io::{BufWriter, Write};
use std::path::Path;
use std::process::Command;
use std::time::Instant;

use clap::{Parser, Subcommand};
use csv::ReaderBuilder;
use git2::{Cred, FetchOptions, RemoteCallbacks, Repository};
use ignore::WalkBuilder;
use serde::Serialize;

/// Dataset builder: filter, clone, analyze (tools + SAST + metadata), collect, or run all.
#[derive(Parser)]
#[command(name = "dataset_builder")]
struct Cli {
    /// GitHub token for authenticated cloning
    #[arg(env = "GITHUB_TOKEN")]
    token: String,

    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    Filter { csv: String, out: String },
    Clone { names: String, out: String },
    Outputs { root: String, outputs: String },
    Collect { root: String, code: String },
    Full {},
}

#[derive(Debug, Serialize)]
struct OutputEntry {
    name: String,
    clippy: String,
    fmt: String,
    audit: String,
    auditable: String,
    deny: String,
    semgrep: String,
    geiger: String,
    codeql: String,
    tree: String,
    ast: String,
    time_ms: Times,
}

#[derive(Debug, Serialize)]
struct Times {
    clippy: u128,
    fmt: u128,
    audit: u128,
    auditable: u128,
    deny: u128,
    semgrep: u128,
    geiger: u128,
    codeql: u128,
    tree: u128,
    ast: u128,
}

#[derive(Debug, Serialize)]
struct CodeEntry {
    name: String,
    path: String,
    content: String,
}

fn main() -> anyhow::Result<()> {
    let cli = Cli::parse();
    match cli.command {
        Commands::Filter { csv, out } => filter_csv(&csv, &out)?,
        Commands::Clone { names, out } => clone_repos(&names, &out, &cli.token)?,
        Commands::Outputs { root, outputs } => run_outputs(&root, &outputs)?,
        Commands::Collect { root, code } => collect_code_all(&root, &code)?,
        Commands::Full {} => run_full(&cli.token)?,
    }
    Ok(())
}

fn filter_csv(input: &str, output: &str) -> anyhow::Result<()> {
    let mut rdr = ReaderBuilder::new().from_path(input)?;
    let mut w = BufWriter::new(File::create(output)?);
    for result in rdr.deserialize::<(String, String, bool, bool)>() {
        let (_id, name, has_toml, has_lock) = result?;
        if has_toml && has_lock {
            writeln!(w, "{}", name)?;
        }
    }
    Ok(())
}

fn clone_repos(names_file: &str, out_root: &str, token: &str) -> anyhow::Result<()> {
    let names = fs::read_to_string(names_file)?;
    for name in names.lines() {
        let dest = Path::new(out_root).join(format!("dataset_{}", sanitize(name)));
        fs::create_dir_all(&dest)?;
        let mut callbacks = RemoteCallbacks::new();
        let tok = token.to_string();
        callbacks.credentials(move |_url, _user, _cred| Cred::userpass_plaintext("x-access-token", &tok));
        let mut fo = FetchOptions::new();
        fo.depth(1).remote_callbacks(callbacks);
        Repository::clone(&format!("https://github.com/{}.git", name), &dest)?;
    }
    Ok(())
}

fn run_outputs(root: &str, outputs_file: &str) -> anyhow::Result<()> {
    let mut w = BufWriter::new(File::create(outputs_file)?);
    for entry in fs::read_dir(root)? {
        let path = entry?.path();
        if !path.is_dir() { continue; }
        let name = path.file_name().unwrap().to_string_lossy();
        let out = analyze_repo(&path, &name)?;
        serde_json::to_writer(&mut w, &out)?;
        w.write_all(b"\n")?;
    }
    Ok(())
}

fn analyze_repo(path: &Path, name: &str) -> anyhow::Result<OutputEntry> {
    let mut times = Times { clippy:0, fmt:0, audit:0, auditable:0, deny:0, semgrep:0, geiger:0, codeql:0, tree:0, ast:0 };
    macro_rules! measure {
        ($field:ident, $func:expr) => {{
            let start = Instant::now();
            let res = $func;
            times.$field = start.elapsed().as_millis();
            res
        }};
    }

    let clippy    = measure!(clippy, run_cmd(path, &["clippy","--message-format=json"])?);
    let fmt       = measure!(fmt, run_cmd(path, &["fmt","--","--check"])?);
    let audit     = measure!(audit, run_cmd(path, &["audit"])?);
    let auditable = measure!(auditable, run_cmd(path, &["auditable"])?);
    let deny      = measure!(deny, run_cmd(path, &["deny","check"])?);
    let geiger    = measure!(geiger, run_cmd(path, &["geiger"])?);
    let tree      = measure!(tree, run_ext_cmd(path, "cargo", &["tree"])?);
    let ast       = measure!(ast, run_ext_cmd(path, "rustc", &["--emit=ast", "-Z", "unpretty=ast"])?);
    let semgrep   = measure!(semgrep, run_ext_cmd(path, "semgrep", &["--config","p/rust","--json"])?);
    let codeql    = measure!(codeql, run_ext_cmd(path, "codeql", &["database","analyze","--format=json"])?);

    Ok(OutputEntry {
        name:      name.into(),
        clippy,
        fmt,
        audit,
        auditable,
        deny,
        semgrep,
        geiger,
        codeql,
        tree,
        ast,
        time_ms:  times,
    })
}

fn run_cmd(dir: &Path, args: &[&str]) -> anyhow::Result<String> {
    let out = Command::new("cargo")
        .current_dir(dir)
        .arg(args[0])
        .args(&args[1..])
        .output()?;
    Ok(String::from_utf8_lossy(if !out.stdout.is_empty() { &out.stdout } else { &out.stderr }).into_owned())
}

fn run_ext_cmd(dir: &Path, cmd: &str, args: &[&str]) -> anyhow::Result<String> {
    let out = Command::new(cmd)
        .current_dir(dir)
        .args(args)
        .output()?;
    Ok(String::from_utf8_lossy(if !out.stdout.is_empty() { &out.stdout } else { &out.stderr }).into_owned())
}

fn collect_code_all(root: &str, code_file: &str) -> anyhow::Result<()> {
    let mut w = BufWriter::new(File::create(code_file)?);
    for entry in fs::read_dir(root)? {
        let path = entry?.path();
        if !path.is_dir() { continue; }
        let name = path.file_name().unwrap().to_string_lossy().into_owned();
        for mut ce in collect_code(&path)? {
            ce.name = name.clone();
            serde_json::to_writer(&mut w, &ce)?;
            w.write_all(b"\n")?;
        }
    }
    Ok(())
}

fn collect_code(repo_path: &Path) -> anyhow::Result<Vec<CodeEntry>> {
    let mut entries = Vec::new();
    WalkBuilder::new(repo_path)
        .standard_filters(true)
        .build()
        .filter_map(Result::ok)
        .filter(|d| d.file_type().map(|t| t.is_file()).unwrap_or(false))
        .filter(|d| {
            let p = d.path();
            !p.starts_with(repo_path.join("target"))
                && !p.starts_with(repo_path.join(".idea"))
                && !p.starts_with(repo_path.join(".vscode"))
        })
        .for_each(|d| {
            if let Ok(content) = fs::read_to_string(d.path()) {
                entries.push(CodeEntry {
                    name: String::new(),
                    path: d.path().strip_prefix(repo_path).unwrap().display().to_string(),
                    content,
                });
            }
        });
    Ok(entries)
}

fn sanitize(name: &str) -> String {
    name.replace('/', "_")
}

fn run_full(token: &str) -> anyhow::Result<()> {
    println!("Starting full dataset extraction pipeline...");
    
    // Step 1: Filter CSV (assuming input.csv exists)
    let input_csv = "input.csv";
    let filtered_repos = "filtered_repos.txt";
    
    if std::path::Path::new(input_csv).exists() {
        println!("Step 1/4: Filtering repositories from {}", input_csv);
        filter_csv(input_csv, filtered_repos)?;
        println!("✓ Filtered repositories saved to {}", filtered_repos);
    } else {
        println!("⚠ Warning: {} not found, skipping filter step", input_csv);
        println!("  Create input.csv with columns: id,name,has_toml,has_lock");
        return Ok(());
    }
    
    // Step 2: Clone repositories
    let datasets_dir = "datasets";
    println!("Step 2/4: Cloning repositories to {}/", datasets_dir);
    clone_repos(filtered_repos, datasets_dir, token)?;
    println!("✓ Repositories cloned successfully");
    
    // Step 3: Run analysis and collect outputs
    let outputs_file = "outputs.jsonl";
    println!("Step 3/4: Running analysis tools and collecting outputs");
    run_outputs(datasets_dir, outputs_file)?;
    println!("✓ Analysis outputs saved to {}", outputs_file);
    
    // Step 4: Collect source code
    let code_file = "code.jsonl";
    println!("Step 4/4: Collecting source code from repositories");
    collect_code_all(datasets_dir, code_file)?;
    println!("✓ Source code collected to {}", code_file);
    
    println!("\n🎉 Full pipeline completed successfully!");
    println!("Generated files:");
    println!("  - {}: Repository analysis and tool outputs", outputs_file);
    println!("  - {}: Source code from all repositories", code_file);
    println!("  - {}/: Downloaded repository datasets", datasets_dir);
    
    Ok(())
}
