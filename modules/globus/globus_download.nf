/**
 * Globus Download Module
 *
 * Downloads ONE file over HTTPS. One task per file, so files download in
 * parallel and a failed file is retried on its own.
 *
 * Input:
 * ------
 * @param tuple:
 *   - relpath:       path of the file in the collection, no leading slash
 *   - size:          size in bytes from the listing
 *   - https_server:  HTTPS address of the collection
 *
 * Output:
 * -------
 * @emit tuple(relpath, the downloaded file), published to params.outdir with its folders
 */
process globus_download_process {
    tag "${relpath}"
    errorStrategy 'retry'
    maxRetries 2
    publishDir "${params.outdir}",
        mode: params.publish_mode,
        saveAs: { fn -> fn.replaceFirst(/^out\//, '') }

    input:
    tuple val(relpath), val(size), val(https_server)

    output:
    tuple val(relpath), path("out/${relpath}", glob: false)

    script:
    """
    export GLOBUS_TOKENS='${params.globus_tokens}'
    python3 /opt/globus_tools/globus_download.py --https-server '${https_server}' --path '${relpath}' --size ${size} --out out
    """

    stub:
    """
    mkdir -p "out/\$(dirname '${relpath}')"
    touch 'out/${relpath}'
    """
}
