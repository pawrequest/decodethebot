import pytest
from loguru import logger
from sqlmodel import Session

from src.DecodeTheBot.models.guru import Guru
from src.DecodeTheBot.models.episode import Episode
from src.DecodeTheBot.dtg_bot import get_matches


# @pytest.mark.asyncio
# async def test_guru_matches_with_matching_title(test_session_with_gurus: Session, random_episode: Episode):
#     logger.info(f"\nmay fail if random ep has no matches: {random_episode}")
#     matches = await guru_matches_(test_session_with_gurus, random_episode)
#     assert len(matches) > 0
#     assert all(isinstance(match, Guru) for match in matches)
#
#
# @pytest.mark.asyncio
# async def test_guru_matches_with_matching_title2(test_session_with_gurus: Session, random_episode: Episode):
#     logger.info(f"\nmay fail if random ep has no matches: {random_episode}")
#     matches = await name_matches_(test_session_with_gurus, random_episode, Guru)
#     assert len(matches) > 0
#     assert all(isinstance(match, Guru) for match in matches)
#
@pytest.mark.asyncio
async def test_all_matches(test_session_with_gurus: Session, random_episode: Episode):
    logger.info(f"\nmay fail if random ep has no matches: {random_episode}")
    matches = get_matches(test_session_with_gurus, random_episode, Guru)
    assert len(matches) > 0
    assert all(isinstance(match, Guru) for match in matches)


#
#
# @pytest.mark.asyncio
# async def test_episode_matches_with_no_matching_title(session: Session, episode: Episode):
#     obj_with_title = type('obj', (object,), {"title": "Non-matching title"})
#     matches = await episode_matches_(session, obj_with_title)
#     assert len(matches) == 0
#
#
# @pytest.mark.asyncio
# async def test_guru_matches_with_matching_name(session: Session, guru: Guru):
#     obj_with_title = type('obj', (object,), {"title": guru.name})
#     matches = await guru_matches_(session, obj_with_title)
#     assert len(matches) > 0
#     assert all(isinstance(match, Guru) for match in matches)
#
#
# @pytest.mark.asyncio
# async def test_guru_matches_with_no_matching_name(session: Session, guru: Guru):
#     obj_with_title = type('obj', (object,), {"title": "Non-matching name"})
#     matches = await guru_matches_(session, obj_with_title)
#     assert len(matches) == 0
#
#
# @pytest.mark.asyncio
# async def test_title_in_title_with_matching_title():
#     model_inst_with_title = type('obj', (object,), {"title": "Matching title"})
#     obj_with_title = type('obj', (object,), {"title": "Matching title"})
#     assert await title_in_title(model_inst_with_title, obj_with_title)
#
#
# @pytest.mark.asyncio
# async def test_title_in_title_with_no_matching_title():
#     model_inst_with_title = type('obj', (object,), {"title": "Matching title"})
#     obj_with_title = type('obj', (object,), {"title": "Non-matching title"})
#     assert not await title_in_title(model_inst_with_title, obj_with_title)
#
#
# @pytest.mark.asyncio
# async def test_name_in_title_with_matching_name():
#     model_inst_with_name = type('obj', (object,), {"name": "Matching name"})
#     obj_with_title = type('obj', (object,), {"title": "Matching name"})
#     assert await name_in_title(model_inst_with_name, obj_with_title)
#
#
# @pytest.mark.asyncio
# async def test_name_in_title_with_no_matching_name():
#     model_inst_with_name = type('obj', (object,), {"name": "Matching name"})
#     obj_with_title = type('obj', (object,), {"title": "Non-matching name"})
#     assert not await name_in_title(model_inst_with_name, obj_with_title)
