#!/usr/bin/env nextflow
nextflow.enable.dsl = 2

/*
 * globus-download-nf -- download everything under paths of a Globus collection.
 *
 *   --collection   Globus collection UUID (required)
 *   --paths        comma separated paths, default '/' (the whole collection)
 *   --outdir       default results
 *
 * Needs the login in GLOBUS_TOKENS (made once with globus_login.py, see README):
 *   --globus_tokens  the login JSON; default: the environment variable globus_tokens, else the Nextflow secret GLOBUS_TOKENS
 */

include { globus_list_process }     from './modules/globus/globus_list.nf'
include { globus_download_process } from './modules/globus/globus_download.nf'
include { md5_verify_process }      from './modules/globus/md5_verify.nf'

workflow {
    if( !params.collection ) {
        error "--collection is required (the Globus collection UUID)"
    }

    // a placeholder the platform did not fill in would fail only inside the first task
    if( params.globus_tokens && params.globus_tokens.toString().contains('{{') ) {
        error "globus_tokens is still a placeholder (text in {{ }}): the platform did not fill it in. Leave --globus_tokens out and set the private variable globus_tokens instead."
    }

    listing = globus_list_process(params.collection, params.paths)

    files = listing.flatMap { f ->
        def j = new groovy.json.JsonSlurper().parseText(f.text)
        j.files.collect { x -> tuple(x.path, x.size, j.https_server) }
    }

    downloaded = globus_download_process(files)

    // one checksum task per folder that has a fastq_md5sum.txt, so no task holds the whole collection
    by_folder = downloaded
        .map { rel, f -> tuple(rel.contains('/') ? rel.substring(0, rel.lastIndexOf('/')) : '', rel, f) }
        .groupTuple(by: 0)
        .filter { dir, rels, fs -> rels.any { it.endsWith('/fastq_md5sum.txt') || it == 'fastq_md5sum.txt' } }

    md5_verify_process(by_folder)
}
