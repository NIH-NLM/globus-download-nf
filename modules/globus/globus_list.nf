/**
 * Globus List Module
 *
 * Lists every file under the given paths of a Globus collection, recursively.
 *
 * Input:
 * ------
 * @param collection: Globus collection UUID
 * @param paths:      comma separated paths ('/' = the whole collection)
 *
 * Output:
 * -------
 * @emit listing.json: {"collection", "https_server", "files": [{"path", "size"}]}
 *
 * The login comes from the secret GLOBUS_TOKENS (see README).
 */
process globus_list_process {
    tag "list_${collection}"
    secret 'GLOBUS_TOKENS'

    input:
    val collection
    val paths

    output:
    path 'listing.json'

    script:
    """
    python3 /opt/globus_tools/globus_list.py --collection '${collection}' --paths '${paths}' --out listing.json
    """

    stub:
    """
    cat > listing.json <<'JSON'
    {"collection": "${collection}", "https_server": "https://example.test",
     "files": [{"path": "A/x.txt", "size": 1}, {"path": "A/y.txt", "size": 1}, {"path": "B/x.txt", "size": 1}]}
    JSON
    """
}
