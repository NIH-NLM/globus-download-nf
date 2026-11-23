#!/usr/bin/env nextflow
nextflow.enable.dsl = 2

/*
 * globus-download-nf -- download everything under paths of a Globus collection.
 *
 *   --collection   Globus collection UUID (required)
 *   --paths        comma separated paths, default '/' (the whole collection)
 *   --batch_size   files per download task, default 10 (the tasks run in parallel)
 *   --outdir       default results
 *
 * Needs the login in GLOBUS_TOKENS (made once with globus_login.py, see README):
 *   --globus_tokens  the login JSON or its base64 (required; on Lifebit a private variable, see README)
 */

include { globus_list_process }     from './modules/globus/globus_list.nf'
include { globus_download_process } from './modules/globus/globus_download.nf'
include { md5_verify_process }      from './modules/globus/md5_verify.nf'

workflow {
    if( !params.collection ) {
        error "--collection is required (the Globus collection UUID)"
    }

    if( !params.globus_tokens ) {
        error "--globus_tokens is required (the login from globus_login.py). On Lifebit: --parameter 'globus_tokens=\${{globus_tokens}}'"
    }
    // a placeholder the platform did not fill in would fail only inside the first task
    if( params.globus_tokens && params.globus_tokens.toString().contains('{{') ) {
        error "globus_tokens is still a placeholder (text in {{ }}): the platform did not fill it in. Check the variable name: it must exist in this workspace."
    }

    tokens = Channel.value(params.globus_tokens)

    listing = globus_list_process(params.collection, params.paths, tokens)

    files = listing.flatMap { f ->
        def j = new groovy.json.JsonSlurper().parseText(f.text)
        j.files.collect { x -> tuple(x.path, x.size, j.https_server) }
    }

    // batches of params.batch_size files; the batches download in parallel
    batches = files
        .buffer(size: params.batch_size as int, remainder: true)
        .map { b -> tuple(b.collect { it[0] }, b.collect { it[1] }, b[0][2]) }

    downloaded = globus_download_process(batches, tokens)
        .flatMap { rels, fs ->
            def list = (fs instanceof List) ? fs : [fs]
            list.collect { f -> tuple(rels.find { r -> f.toString().endsWith('/out/' + r) }, f) }
        }

    // one checksum task per folder that has a fastq_md5sum.txt, so no task holds the whole collection
    by_folder = downloaded
        .map { rel, f -> tuple(rel.contains('/') ? rel.substring(0, rel.lastIndexOf('/')) : '', rel, f) }
        .groupTuple(by: 0)
        .filter { dir, rels, fs -> rels.any { it.endsWith('/fastq_md5sum.txt') || it == 'fastq_md5sum.txt' } }

    md5_verify_process(by_folder)
}
