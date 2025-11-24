-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:34 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_2 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_3 = require(game.ReplicatedStorage.Lobby.UI.QueuedDisplaySection)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_5 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_6 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_7 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_8 = require(game.ReplicatedStorage.AudioData.SongElementalColor)
local v_u_9 = require(game.ReplicatedStorage.Avatar.ElementalColor)
local v_u_10 = require(game.ReplicatedStorage.Shared.SPDict)
return {
    ["new"] = function(_, p_u_11) --[[ Name: new ]] --[[ Line: 17 ]]
        --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_1, (copy 3): v_u_3, (copy 4): v_u_5, (copy 5): v_u_6, (copy 6): v_u_10, (copy 7): v_u_9, (copy 8): v_u_2, (copy 9): v_u_8, (copy 10): v_u_7 ]]
        local v12 = {
            ["update"] = function(_, _) end
        }
        local v_u_13 = v_u_4:new()
        local v_u_14 = v_u_4:new()
        local v_u_15 = v_u_4:new()
        local v_u_16 = v_u_4:new()
        local v_u_17 = v_u_4:new()
        local v_u_18 = v_u_4:new()
        local function f_cons() --[[ Name: cons ]] --[[ Line: 40 ]]
            --[[ Upvalues: (ref 1): v_u_1, (copy 2): v_u_13, (ref 3): v_u_3, (copy 4): v_u_14, (copy 5): v_u_15, (copy 6): v_u_16, (copy 7): v_u_17, (copy 8): v_u_18 ]]
            local l_SurfaceGui_0 = v_u_1:get_lobby_environment().SubwayClub.MainDisplay.Screen.SurfaceGui
            v_u_13:push_back(l_SurfaceGui_0)
            local l_SurfaceGui_1 = v_u_1:get_lobby_environment().SubwayClub.DJTable.Display.Screen.SurfaceGui
            v_u_13:push_back(l_SurfaceGui_1)
            local v19 = v_u_3:new(l_SurfaceGui_0.Frame.NowPlayingSection)
            v19:set_song_title_display(v19:get_section_root().TitleDisplay)
            v19:set_artist_display(v19:get_section_root().ArtistDisplay)
            v19:set_cover_and_overlay_image(v19:get_section_root().SongIcon.Icon, v19:get_section_root().SongIcon.IconOverlay)
            v19:set_time_remaining_display(v19:get_section_root().TimeRemainingSection.TimeRemainingDisplay)
            v19:set_queued_by_display(v19:get_section_root().QueuerDisplay)
            v19:set_vote_bar_section(v19:get_section_root().BarSection.BarFillUp, v19:get_section_root().BarSection.BarFillDown, v19:get_section_root().BarSection.UpVoteDisplay, v19:get_section_root().BarSection.DownVoteDisplay, v19:get_section_root().BarSection.VotesToSkipDisplay)
            v19:update_vote_bar_fill(0, 0)
            v19:update_vote_to_skip_count(0)
            v_u_14:push_back(v19)
            local v20 = v_u_3:new(l_SurfaceGui_1.Frame.NowPlayingSection)
            v20:set_song_title_display(v20:get_section_root().TitleDisplay)
            v20:set_artist_display(v20:get_section_root().ArtistDisplay)
            v20:set_cover_and_overlay_image(v20:get_section_root().SongIcon.Icon, v20:get_section_root().SongIcon.IconOverlay)
            v20:set_time_remaining_display(v20:get_section_root().TimeRemainingSection.TimeRemainingDisplay)
            v20:set_queued_by_display(v20:get_section_root().QueuerDisplay)
            v_u_14:push_back(v20)
            local v21 = v_u_3:new(l_SurfaceGui_0.Frame.UpNextSection)
            v21:set_song_title_display(v21:get_section_root().TitleDisplay)
            v21:set_artist_display(v21:get_section_root().ArtistDisplay)
            v21:set_cover_and_overlay_image(v21:get_section_root().SongIcon.Icon, v21:get_section_root().SongIcon.IconOverlay)
            v21:set_queued_by_display(v21:get_section_root().QueuerDisplay)
            v21:set_queue_status_display(v21:get_section_root().SongsQueuedCountDisplay)
            v_u_15:push_back(v21)
            v_u_16:push_back(l_SurfaceGui_0.Frame.NowPlayingEmptyText)
            v_u_16:push_back(l_SurfaceGui_1.Frame.NowPlayingEmptyText)
            v_u_17:push_back(l_SurfaceGui_0.Frame.UpNextEmptyText)
            local l_Tiles_0 = v_u_1:get_lobby_environment().SubwayClub.Floor.Tiles
            for v22 = 1, 96 do
                v_u_18:push_back(l_Tiles_0:FindFirstChild((tostring(v22))))
            end;
        end;
        v12.set_club_uis_visible = function(_, p23) --[[ Name: set_club_uis_visible ]] --[[ Line: 126 ]]
            --[[ Upvalues: (copy 1): v_u_13 ]]
            for v24 = 1, v_u_13:count() do
                v_u_13:get(v24).Enabled = p23
            end;
        end;
        v12.sync_ui_to_dance_club_manager = function(_) --[[ Name: sync_ui_to_dance_club_manager ]] --[[ Line: 133 ]]
            --[[ Upvalues: (copy 1): v_u_14, (copy 2): p_u_11, (ref 3): v_u_5, (ref 4): v_u_6, (copy 5): v_u_16, (copy 6): v_u_15, (copy 7): v_u_17 ]]
            for v25 = 1, v_u_14:count() do
                local v26 = v_u_14:get(v25)
                local v27, v28, v29, v30, v31, v32, v33, _ = p_u_11._dance_club_manager:get_current_song_info()
                if v_u_5:singleton():contains_key(v27) then
                    v26:set_visible(true)
                    v26:set_songid(v27)
                    v26:set_time_remaining_text(string.format("%s / %s", v_u_6:format_ms_time(v28 * 1000), v_u_6:format_ms_time(v29 * 1000)))
                    v26:set_queued_by_text(string.format("Queued by: %s", v30))
                    v26:update_vote_bar_fill(v31, v32)
                    v26:update_vote_to_skip_count(v33)
                else
                    v26:set_visible(false)
                end;
            end;
            for v34 = 1, v_u_16:count() do
                local v35 = v_u_16:get(v34)
                local v36, _, _, _ = p_u_11._dance_club_manager:get_current_song_info()
                if v_u_5:singleton():contains_key(v36) then
                    v35.Visible = false
                else
                    v35.Visible = true
                end;
            end;
            for v37 = 1, v_u_15:count() do
                local v38 = v_u_15:get(v37)
                local v39, v40, v41 = p_u_11._dance_club_manager:get_next_song_info()
                if v_u_5:singleton():contains_key(v39) then
                    v38:set_visible(true)
                    v38:set_songid(v39)
                    v38:set_queued_by_text(string.format("Queued by: %s", v40))
                    v38:set_queue_status_text(string.format("%d Song(s) Queued", v41))
                else
                    v38:set_visible(false)
                end;
            end;
            for v42 = 1, v_u_17:count() do
                local v43 = v_u_17:get(v42)
                local v44, _, _ = p_u_11._dance_club_manager:get_next_song_info()
                if v_u_5:singleton():contains_key(v44) then
                    v43.Visible = false
                else
                    v43.Visible = true
                end;
            end;
        end;
        v12.sync_ui_now_playing_time_remaining_to_dance_club_manager = function(_) --[[ Name: sync_ui_now_playing_time_remaining_to_dance_club_manager ]] --[[ Line: 184 ]]
            --[[ Upvalues: (copy 1): v_u_14, (copy 2): p_u_11, (ref 3): v_u_5, (ref 4): v_u_6 ]]
            for v45 = 1, v_u_14:count() do
                local v46 = v_u_14:get(v45)
                local v47, v48, v49, _ = p_u_11._dance_club_manager:get_current_song_info()
                if v_u_5:singleton():contains_key(v47) then
                    v46:set_time_remaining_text(string.format("%s / %s", v_u_6:format_ms_time(v48 * 1000), v_u_6:format_ms_time(v49 * 1000)))
                else
                    v46:set_visible(false)
                end;
            end;
        end;
        local v_u_50 = 0
        v12.update_club_uis = function(p51, p52) --[[ Name: update_club_uis ]] --[[ Line: 200 ]]
            --[[ Upvalues: (copy 1): p_u_11, (ref 2): v_u_50, (ref 3): v_u_6 ]]
            if p_u_11._dance_club_manager:get_synced_time() == v_u_50 then
                p51:sync_ui_now_playing_time_remaining_to_dance_club_manager()
            else
                v_u_50 = p_u_11._dance_club_manager:get_synced_time()
                p51:sync_ui_to_dance_club_manager()
            end;
            v_u_6:profilebegin("LobbyEnvManager:update_club_tiles")
            p51:update_club_tiles(p52)
            v_u_6:profileend()
        end;
        local v_u_53 = v_u_10:new({
            [v_u_9.Blue] = Color3.fromRGB(83, 119, 249),
            [v_u_9.Green] = Color3.fromRGB(68, 249, 95),
            [v_u_9.Orange] = Color3.fromRGB(175, 109, 29),
            [v_u_9.Purple] = Color3.fromRGB(125, 45, 175),
            [v_u_9.Red] = Color3.fromRGB(175, 30, 49)
        })
        local v_u_54 = v_u_10:new({
            [v_u_9.Blue] = Color3.fromRGB(67, 99, 202),
            [v_u_9.Green] = Color3.fromRGB(42, 116, 60),
            [v_u_9.Orange] = Color3.fromRGB(129, 91, 37),
            [v_u_9.Purple] = Color3.fromRGB(106, 32, 124),
            [v_u_9.Red] = Color3.fromRGB(120, 58, 49)
        })
        local v_u_55 = 0
        local v_u_56 = 0
        v12.update_club_tiles = function(_, p57) --[[ Name: update_club_tiles ]] --[[ Line: 231 ]]
            --[[ Upvalues: (copy 1): p_u_11, (ref 2): v_u_5, (copy 3): v_u_18, (ref 4): v_u_55, (ref 5): v_u_2, (ref 6): v_u_56, (ref 7): v_u_8, (copy 8): v_u_53, (copy 9): v_u_54, (ref 10): v_u_7 ]]
            local v_u_58, _, _, _ = p_u_11._dance_club_manager:get_current_song_info()
            if v_u_5:singleton():contains_key(v_u_58) then
                if v_u_18:get(1).Material ~= Enum.Material.Neon then
                    for v59 = 1, v_u_18:count() do
                        v_u_18:get(v59).Material = Enum.Material.Neon
                        v_u_18:get(v59).Transparency = 0.15
                    end;
                end;
                local v60, v61 = v_u_2:IncrementWrap(v_u_55, v_u_2:sec_to_tick(3.5) * p57, 1)
                v_u_55 = v60
                if v61 then
                    if v_u_56 == 0 then
                        v_u_56 = 1
                    else
                        v_u_56 = 0
                    end;
                end;
                local v_u_62 = Color3.fromRGB()
                local v_u_63 = Color3.fromRGB()
                local v65, v66 = pcall(function() --[[ Line: 256 ]]
                    --[[ Upvalues: (ref 1): v_u_8, (copy 2): v_u_58, (ref 3): v_u_62, (ref 4): v_u_53, (ref 5): v_u_63, (ref 6): v_u_54 ]]
                    local v64 = v_u_8:songkey_get_color_list(v_u_58)
                    if v64:count() >= 2 then
                        v_u_62 = v_u_53:get(v64:get(1))
                        v_u_63 = v_u_54:get(v64:get(2))
                    elseif v64:count() == 1 then
                        v_u_62 = v_u_53:get(v64:get(1))
                        v_u_63 = v_u_54:get(v64:get(1))
                    end;
                end)
                if not v65 then
                    v_u_7:warnf("LobbyEnvManager:update_club_tiles: %s", v66)
                end;
                local v67, v68
                if v_u_56 == 1 then
                    local v69 = v_u_62
                    v_u_62 = v_u_63
                    v_u_63 = v69
                    v67 = v_u_62
                    v68 = v_u_63
                else
                    v67 = v_u_62
                    v68 = v_u_63
                end;
                for v70 = 1, v_u_18:count() do
                    local v71
                    if math.ceil(v70 / 6) % 2 == 0 then
                        if v70 % 2 == 0 then
                            v71 = v68
                        else
                            v71 = v67
                        end;
                    elseif v70 % 2 == 0 then
                        v71 = v67
                    else
                        v71 = v68
                    end;
                    local l_Color_0 = v_u_18:get(v70).Color
                    if l_Color_0 ~= v71 then
                        local v72 = v_u_2:YForPointOf2PtLineP1P2X(1, 2, v_u_18:count(), 0.15, v70)
                        v_u_18:get(v70).Color = Color3.new(v_u_2:Expt(l_Color_0.r, v71.r, v_u_2:NormalizedDefaultExptValueInSeconds(v72), p57), v_u_2:Expt(l_Color_0.g, v71.g, v_u_2:NormalizedDefaultExptValueInSeconds(v72), p57), v_u_2:Expt(l_Color_0.b, v71.b, v_u_2:NormalizedDefaultExptValueInSeconds(v72), p57))
                    end;
                end;
            end;
        end;
        f_cons()
        return v12;
    end
};
