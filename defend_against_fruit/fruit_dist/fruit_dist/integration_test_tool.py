import argparse
import json
import logging
from fruit_dist.artifactory.artifactory_rest import publish_build_info, build_promote
from fruit_dist.build.agent import Agent
from fruit_dist.build.build_info import BuildInfo
from fruit_dist.build.build_retention import BuildRetention
from fruit_dist.build.constants import PYTHON_SDIST, PYTHON_FREEZE
from fruit_dist.build.id import Id
from fruit_dist.build.module import Module
from fruit_dist.build.promotion_request import PromotionRequest
from fruit_dist.build_info_utils import build_info_to_text


def execute():
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

    args = _parse_args()
    sub_command_function = args.func
    sub_command_function(args)


def _parse_args(args=None):
    parser = argparse.ArgumentParser(
        description='Integration test utility for testing Artifactory Rest API calls.')

    parser.add_argument('--username', action='store', default="admin", help='Artifactory username')
    parser.add_argument('--password', action='store', default="password", help='Artifactory password')
    parser.add_argument(
        '--base_url',
        action='store',
        required=True,
        help='Artifactory password'
    )
    parser.add_argument('--ignore-cert-errors', action='store_true', default=False, help='Verify certificate')

    subparsers = parser.add_subparsers(title="subcommands", description="Various subcommands for testing")

    parser_build_info = subparsers.add_parser('build-info')
    parser_build_info.add_argument('--name', action='store', required=True, help="name to use in build-info")
    parser_build_info.add_argument('--number', action='store', required=True, help="build number to use in build-info")
    parser_build_info.set_defaults(func=_build_info)

    #build_name, build_number
    parser_build_info = subparsers.add_parser('build-promote')
    parser_build_info.add_argument('--name', action='store', required=True, help="build name to promote")
    parser_build_info.add_argument('--number', action='store', required=True, help="build number to promote")
    parser_build_info.set_defaults(func=_build_promote)

    return parser.parse_args(args)


def _build_promote(args):
    my_build_number = args.number
    my_build_name = args.name
    promotion_request = PromotionRequest(
        status="monkey",
        comment="promoted using integration test tool",
        ci_user="builder",
        timestamp="2013-03-21T11:30:06.143-0500",
        dry_run=False,
        target_repo="pypi-teamfruit-2-local",
        properties={
            "components": ["c1", "c3", "c14"],
            "release-name": ["fb3-ga"]}
    )
    promotion_request_as_text = json.dumps(promotion_request.as_json_data, sort_keys=True, indent=4)
    logging.debug(promotion_request_as_text)

    promotion_response_json = build_promote(
        username=args.username,
        password=args.password,
        repo_base_url=args.base_url,
        build_name=my_build_name,
        build_number=my_build_number,
        promotion_request=promotion_request,
        verify_cert=not args.ignore_cert_errors
    )

    print "Promotion Response {}".format(promotion_response_json)


def _build_info(args):
    my_build_number = args.number
    my_build_name = args.name

    bi_builder = BuildInfo.Builder(
        version="2.2.2",
        name=my_build_name,
        number=my_build_number,
        type='GENERIC',  # Looks like valid values are "GENERIC", "MAVEN", "ANT", "IVY" and "GRADLE"
        started="2013-03-21T10:49:01.143-0500",  # Looks like time format is very specific
        duration_millis=10000,
        artifactory_principal="dude",
        agent=Agent(name="defend_against_fruit", version="5.2"),
        build_agent=Agent(name="TeamCity", version="1.3"),
        build_retention=BuildRetention(
            count=-1,
            delete_build_artifacts=False,
            build_numbers_not_to_be_discarded=[111, 999])  # Is this for TeamCity "pinned" builds?
    )
    module_builder = Module.Builder(id=Id(group_id="python", artifact_id="fruit_dist", version="1.2.15"))
    module_builder.add_artifact(
        type=PYTHON_SDIST,
        name="fruit_dist-1.2.15.tar.gz",
        sha1="0a66f5619bcce7a441740e154cd97bad04189d86",
        md5="2a17acbb714e7b696c58b4ca6e07c611")
    module_builder.add_artifact(
        type=PYTHON_FREEZE,
        name="fruit_dist-1.2.15-requirements.txt",
        sha1="06e5f0080b6b15704be9d78e801813d802a90625",
        md5="254c0e43bbf5979f8b34ff0428ed6931"
    )
    module_builder.add_dependency(
        type=PYTHON_SDIST,
        id=Id(group_id="python", artifact_id="nose", version="1.2.1"),
        sha1="02cc3ffdd7a1ce92cbee388c4a9e939a79f66ba5",
        md5="735e3f1ce8b07e70ee1b742a8a53585a")

    bi_builder.add_module(module_builder.build())

    build_info = bi_builder.build()

    logging.debug(build_info_to_text(build_info))

    publish_build_info(
        username=args.username,
        password=args.password,
        repo_base_url=args.base_url,
        build_info=build_info,
        verify_cert=not args.ignore_cert_errors
    )


if __name__ == "__main__":
    execute()