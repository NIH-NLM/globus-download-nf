/**
 * MD5 Verify Module
 *
 * Checks the downloaded files against every fastq_md5sum.txt in the downloaded
 * folders. A mismatch, a missing file or an unreadable line fails the run.
 * Data is never deleted. The problem files are printed to the task's stderr.
 *
 * One task per folder, so a task only holds the files of one folder.
 *
 * Input:
 * ------
 * @param tuple:
 *   - dir:      folder in the collection ('' for the top)
 *   - relpaths: list of file paths in the collection (same order as files)
 *   - files:    the downloaded files, each staged in its own folder (stage1/, stage2/, ...)
 *
 * Output:
 * -------
 * @emit md5_reports/<folder>.json: list of {folder, file, expected, actual, ok}
 */
process md5_verify_process {
    tag "${dir ?: 'top'}"
    publishDir "${params.outdir}",
        mode: params.publish_mode,
        saveAs: { fn -> "md5_reports/${(dir ?: 'top').replace('/', '__')}.json" }

    input:
    tuple val(dir), val(relpaths), path(files, stageAs: 'stage?/*')

    output:
    path 'md5_report.json'

    script:
    def links = relpaths.indexed(1).collect { i, rel ->
        "mkdir -p \"tree/\$(dirname '${rel}')\" && ln -s \"\$PWD/stage${i}/\$(basename '${rel}')\" 'tree/${rel}'"
    }.join('\n')
    """
    mkdir -p tree
    ${links}
    python3 /opt/globus_tools/md5_verify.py --root tree --out md5_report.json
    """

    stub:
    """
    echo '[]' > md5_report.json
    """
}
