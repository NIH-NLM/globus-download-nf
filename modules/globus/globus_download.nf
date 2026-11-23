/**
 * Globus Download Module
 *
 * Downloads one BATCH of files over HTTPS (params.batch_size files, one after
 * the other). Batches run in parallel, so many files download at once while
 * the number of connections to the server stays small. A file that fails does
 * not stop the rest of its batch, but the task fails at the end and names it.
 *
 * Input:
 * ------
 * @param tuple:
 *   - relpaths:      list of file paths in the collection, no leading slash
 *   - sizes:         list of sizes in bytes from the listing (same order)
 *   - https_server:  HTTPS address of the collection
 * @param GLOBUS_TOKENS: the login (JSON or base64), handed over as an environment
 *                    variable so it is not part of the command text
 *
 * Output:
 * -------
 * @emit tuple(relpaths, the downloaded files), published to params.outdir with their folders
 */
process globus_download_process {
    tag "${relpaths[0]} +${relpaths.size() - 1}"
    errorStrategy 'retry'
    maxRetries 2
    publishDir "${params.outdir}",
        mode: params.publish_mode,
        saveAs: { fn -> fn.replaceFirst(/^out\//, '') }

    input:
    tuple val(relpaths), val(sizes), val(https_server)
    env 'GLOBUS_TOKENS'

    output:
    tuple val(relpaths), path('out/**')

    script:
    def tsv = [relpaths, sizes].transpose().collect { p, s -> "${p}\t${s}" }.join('\n')
    """
cat > batch.tsv <<'EOF_BATCH'
${tsv}
EOF_BATCH
    python3 /opt/globus_tools/globus_download.py --https-server '${https_server}' --manifest batch.tsv --out out
    """

    stub:
    def makes = relpaths.collect { "mkdir -p \"out/\$(dirname '${it}')\" && touch 'out/${it}'" }.join('\n')
    """
    ${makes}
    """
}
