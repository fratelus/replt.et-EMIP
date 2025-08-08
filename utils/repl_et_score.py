import os
import json
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for headless environments
import matplotlib.pyplot as plt
import numpy as np

def check_metadata():
    try:
        with open("metadata.json") as f:
            data = json.load(f)
        required = ["study_title", "paradigm", "task_description"]
        if all(k in data and data[k] for k in required):
            return 1.0
        elif any(k in data for k in required):
            return 0.5
        else:
            return 0.25
    except Exception:
        return 0

def check_participants():
    path = "participants/participants.json"
    if not os.path.exists(path):
        return 0
    try:
        with open(path) as f:
            data = json.load(f)
        if "participants" in data and len(data["participants"]) > 0:
            fields = ["age", "gender", "handedness", "vision"]
            has_fields = all(all(field in p for field in fields) for p in data["participants"])
            if has_fields:
                return 1.0
            else:
                return 0.75
        else:
            return 0.25
    except Exception:
        return 0

def check_equipment():
    files = ["equipment/tracker_specs.json", "equipment/screen_setup.json", "equipment/software_env.json"]
    found = sum(os.path.exists(f) for f in files)
    if found == 3:
        return 1.0
    elif found == 2:
        return 0.75
    elif found == 1:
        return 0.5
    else:
        return 0

def check_stimuli():
    meta = "stimuli/stimuli_metadata.json"
    ann = "stimuli/stimuli_annotations.json"
    raw = "stimuli/stimuli_raw"
    score = 0
    if os.path.exists(meta):
        score += 0.4
    if os.path.exists(ann):
        score += 0.3
    if os.path.isdir(raw) and len(os.listdir(raw)) > 0:
        score += 0.3
    return min(score, 1.0)

def check_aois():
    aois = "aois/aois_definition.json"
    vis = "aois/aois_visualizations"
    if os.path.exists(aois):
        if os.path.isdir(vis) and len(os.listdir(vis)) > 0:
            return 1.0
        else:
            return 0.75
    else:
        return 0

def check_data_quality():
    proto = "collection/protocol.json"
    logs = "collection/logs"
    if os.path.exists(proto):
        if os.path.isdir(logs) and len(os.listdir(logs)) > 0:
            return 1.0
        else:
            return 0.75
    else:
        return 0

def check_preprocessing():
    pre = "preprocessing/preprocessing.json"
    scripts = "preprocessing/scripts"
    if os.path.exists(pre):
        if os.path.isdir(scripts) and len(os.listdir(scripts)) > 0:
            return 1.0
        else:
            return 0.75
    else:
        return 0

def check_analysis():
    ana = "analysis/analysis.json"
    tables = "analysis/results_tables"
    vis = "analysis/visualizations"
    score = 0
    if os.path.exists(ana):
        score += 0.5
    if os.path.exists(tables) and len(os.listdir(tables)) > 0:
        score += 0.25
    if os.path.exists(vis) and len(os.listdir(vis)) > 0:
        score += 0.25
    return min(score, 1.0)

def check_threats():
    val = "validity/validity.json"
    if os.path.exists(val):
        with open(val) as f:
            data = json.load(f)
        if "threats" in data and len(data["threats"]) > 0:
            return 1.0
        else:
            return 0.5
    else:
        return 0

def check_reproducibility():
    files = ["README.md", "LICENSE", "reproducibility/reproducibility.json", "CITATION.cff"]
    found = sum(os.path.exists(f) for f in files)
    if found == len(files):
        return 1.0
    elif found >= 3:
        return 0.75
    elif found >= 2:
        return 0.5
    elif found >= 1:
        return 0.25
    else:
        return 0

def update_readme_with_assessment(scores, overall_score, png_path):
    """Update README.md with current assessment results"""
    try:
        # Map scores to readable names
        score_mapping = {
            "metadata": "Study Metadata",
            "participants": "Participant Info", 
            "equipment": "Equipment Specs",
            "stimuli": "Stimuli & Materials",
            "aois": "Areas of Interest",
            "data_quality": "Data Quality & Collection",
            "preprocessing": "Data Preprocessing",
            "analysis": "Statistical Analysis",
            "threats": "Validity Assessment",
            "reproducibility": "Reproducibility Materials"
        }
        
        # Calculate compliance
        compliant_criteria = sum(1 for score in scores.values() if score > 0.8)
        total_criteria = len(scores)
        compliance_percentage = (compliant_criteria / total_criteria) * 100 if total_criteria > 0 else 0
        
        # Determine status
        if compliance_percentage >= 80:
            template_status = "Complete"
            result_message = "Publication Ready"
        elif compliance_percentage >= 50:
            template_status = "In Progress"  
            result_message = "Good Progress"
        else:
            template_status = "Starting"
            result_message = "Empty Template" if compliance_percentage < 30 else "Basic Setup"
        
        # Generate checklist markdown
        checklist_items = []
        for component, score in scores.items():
            status = "✅" if score > 0.8 else "⚠️" if score > 0.5 else "❌"
            readable_name = score_mapping.get(component, component.replace("_", " ").title())
            checklist_items.append(f"- {status} **{readable_name}**: {score*100:.1f}%")
        
        checklist_md = f"""## 📋 Compliance Checklist

**Status**: {template_status} ({result_message})  
**Overall Compliance**: {compliant_criteria}/{total_criteria} criteria met ({compliance_percentage:.1f}%)

### Component Scores:
{chr(10).join(checklist_items)}

### Legend:
- ✅ **Complete** (>80%): Publication ready
- ⚠️ **Partial** (50-80%): Good progress, needs refinement  
- ❌ **Missing** (<50%): Requires attention

---
"""
        
        # Generate scores table
        rows = []
        for component, score in scores.items():
            readable_name = score_mapping.get(component, component.replace("_", " ").title())
            rows.append(f"| {readable_name} | {score*100:.1f}% |")
        
        scores_table_md = f"""
| Study Component | Score |
|----------------|-------|
{chr(10).join(rows)}
| **Overall Study Score** | **{overall_score*100:.1f}%** |
"""
        
        # Read current README
        readme_path = 'README.md'
        if os.path.exists(readme_path):
            with open(readme_path, 'r', encoding='utf-8') as f:
                content = f.read()
        else:
            content = "# Study Assessment\n\n"
        
        # Update checklist section
        import re
        checklist_pattern = r'(## 📋 Compliance Checklist.*?)(?=##|\Z)'
        if re.search(checklist_pattern, content, re.DOTALL):
            content = re.sub(checklist_pattern, checklist_md + '\n', content, flags=re.DOTALL)
        else:
            # Find the Template Compliance Analysis section and add after it
            template_section = "## Template Compliance Analysis"
            if template_section in content:
                content = content.replace(template_section, template_section + '\n\n' + checklist_md)
            else:
                content += '\n' + checklist_md + '\n'
        
        # Update scores table section  
        scores_pattern = r'(\| Study Component \| Score.*?\*\*Overall Study Score.*?\*\*[^\n]*)'
        if re.search(scores_pattern, content, re.DOTALL):
            content = re.sub(scores_pattern, scores_table_md.strip(), content, flags=re.DOTALL)
        else:
            # Add scores table after checklist
            content += '\n' + scores_table_md + '\n'
        
        # Update spider graph image
        spider_pattern = r'!\[Reproducibility Spider Graph\]\([^)]+\)'
        spider_replacement = f'![Reproducibility Spider Graph]({png_path})'
        if re.search(spider_pattern, content):
            content = re.sub(spider_pattern, spider_replacement, content)
        else:
            content += f'\n{spider_replacement}\n'
        
        # Write updated README
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"📝 README.md updated with assessment results!")
        print(f"📊 Compliance: {compliant_criteria}/{total_criteria} ({compliance_percentage:.1f}%)")
        print(f"🏷️ Status: {template_status}")
        
    except Exception as e:
        print(f"⚠️ Warning: Could not update README: {e}")

def main():
    scores = {
        "metadata": check_metadata(),
        "participants": check_participants(),
        "equipment": check_equipment(),
        "stimuli": check_stimuli(),
        "aois": check_aois(),
        "data_quality": check_data_quality(),
        "preprocessing": check_preprocessing(),
        "analysis": check_analysis(),
        "threats": check_threats(),
        "reproducibility": check_reproducibility()
    }
    
    # Create output directory
    import os
    output_dir = "outputs"
    os.makedirs(output_dir, exist_ok=True)
    
    # Salva JSON
    json_path = os.path.join(output_dir, "report.json")
    with open(json_path, "w") as f:
        json.dump(scores, f, indent=2)
    
    # Enhanced spider graph with better labels and styling
    criteria_labels = {
        'metadata': 'Study\nMetadata',
        'participants': 'Participant\nInfo',
        'equipment': 'Equipment\nSpecs',
        'stimuli': 'Stimuli\n& Materials',
        'aois': 'Areas of\nInterest',
        'data_quality': 'Data Quality\n& Collection',
        'preprocessing': 'Data\nPreprocessing',
        'analysis': 'Statistical\nAnalysis',
        'threats': 'Validity\nThreats',
        'reproducibility': 'Reproducibility\nMaterials'
    }
    
    # Get criteria in consistent order
    criteria = list(criteria_labels.keys())
    labels = [criteria_labels[c] for c in criteria]
    values = [scores.get(c, 0.0) for c in criteria]
    
    # Close the radar chart
    angles = np.linspace(0, 2*np.pi, len(criteria), endpoint=False).tolist()
    values += values[:1]
    angles += angles[:1]
    
    # Calculate overall score for coloring
    overall_score = sum(scores.values()) / len(scores)
    if overall_score >= 0.8:
        color = '#2ecc71'  # Green for excellent
    elif overall_score >= 0.6:
        color = '#f39c12'  # Orange for good
    elif overall_score >= 0.4:
        color = '#e74c3c'  # Red for needs improvement
    else:
        color = '#95a5a6'  # Gray for baseline/template
    
    # Create the spider plot
    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(polar=True))
    ax.plot(angles, values, 'o-', linewidth=3, color=color, markersize=8)
    ax.fill(angles, values, alpha=0.25, color=color)
    
    # Customize the chart
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=11)
    ax.set_ylim(0, 1.0)
    ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_yticklabels(['0.2', '0.4', '0.6', '0.8', '1.0'], fontsize=10)
    ax.grid(True, alpha=0.3)
    
    # Add title with score
    plt.title(f'ReplET Reproducibility Analysis\n{overall_score*100:.1f}% Overall Score', 
              fontsize=16, fontweight='bold', pad=30)
    
    # Add value labels for non-zero scores
    for angle, value, label in zip(angles[:-1], values[:-1], labels):
        if value > 0.05:  # Only show labels for significant values
            ax.text(angle, value + 0.08, f'{value:.2f}', 
                   ha='center', va='center', fontsize=10, fontweight='bold',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.9, edgecolor=color))
    
    plt.tight_layout()
    
    png_path = os.path.join(output_dir, "score.png")
    plt.savefig(png_path)
    
    # Gera report.md
    md_path = os.path.join(output_dir, "report.md")
    with open(md_path, "w") as f:
        f.write("# Repl.ET Replicability Report\n\n")
        for k, v in scores.items():
            f.write(f"- **{k}**: {v}\n")
        f.write(f"\nVeja score.png para o gráfico radar.\n")
    
    # Print location of generated files
    print(f"📊 Reproducibility Report Generated!")
    print(f"📁 Output directory: {output_dir}")
    print(f"📄 JSON report: {json_path}")
    print(f"📈 Radar chart: {png_path}")
    print(f"📝 Markdown report: {md_path}")
    
    # Calculate overall score
    overall_score = sum(scores.values()) / len(scores)
    print(f"\n🏆 Overall Reproducibility Score: {overall_score:.3f}/1.0 ({overall_score*100:.1f}%)")
    
    # Update README with assessment
    update_readme_with_assessment(scores, overall_score, png_path)

if __name__ == "__main__":
    main() 