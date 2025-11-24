-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:51 PM
-- Time elapsed: 19 milliseconds

local v_u_1 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPMultiDict)
require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_2 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.Shared.AssertType)
local v_u_3 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_4 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_6 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_7 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_8 = require(game.ReplicatedStorage.PlayerInfo.VIPInfo)
require(game.ReplicatedStorage.AudioData.SongElementalColor)
local v_u_9 = require(game.ReplicatedStorage.AudioData.AudioMod)
local v_u_10 = require(game.ReplicatedStorage.AudioData.NewSongInfo)
local v_u_11 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_12 = require(game.ReplicatedStorage.Shared.AudioRank)
local v_u_13 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
local v_u_14 = require(game.ReplicatedStorage.PlayerInfo.Collection.CollectionInfo)
local v_u_15 = require(game.ReplicatedStorage.Avatar.ElementalColor)
local v_u_16 = require(game.ReplicatedStorage.AudioData.SongElementalColor)
local v_u_17 = require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
local v_u_18 = require(game.ReplicatedStorage.Shared.PlayerSongPlay)
local v_u_19 = require(game.ReplicatedStorage.Shared.MatchMode)
local v20 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_21 = nil
local v_u_22 = nil
local v_u_23 = nil
local v_u_24 = nil
local v_u_25 = nil
v20:require_client(function() --[[ Line: 33 ]]
    --[[ Upvalues: (ref 1): v_u_21, (ref 2): v_u_22, (ref 3): v_u_23, (ref 4): v_u_24, (ref 5): v_u_25 ]]
    v_u_21 = require(game.ReplicatedStorage.Lobby.Menus.PreviewImageUI)
    v_u_22 = require(game.ReplicatedStorage.Lobby.Menus.MatchMakingV3UI)
    v_u_23 = require(game.ReplicatedStorage.Lobby.Menus.CraftSongUI)
    v_u_24 = require(game.ReplicatedStorage.EditorGame.UI.SavedMapInfoListUI)
    v_u_25 = require(game.ReplicatedStorage.Lobby.Menus.ListSelectUI)
end)
local v_u_52 = {
    ["new"] = function(_, p_u_26, p_u_27, p_u_28) --[[ Name: new ]] --[[ Line: 50 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_9, (copy 3): v_u_8, (copy 4): v_u_4, (copy 5): v_u_10, (copy 6): v_u_11, (copy 7): v_u_16, (copy 8): v_u_5, (copy 9): v_u_12 ]]
        local v29 = {}
        local v_u_30 = nil
        local v_u_31 = nil
        local v_u_32 = nil
        local v_u_33 = nil
        local v_u_34 = nil
        local v_u_35 = nil
        local v_u_36 = nil
        local v_u_37 = nil
        local v_u_38 = nil
        local v_u_39 = v_u_3:invalid_songkey()
        v29.get_element_data = function(_) --[[ Name: get_element_data ]] --[[ Line: 62 ]]
            --[[ Upvalues: (ref 1): v_u_39 ]]
            return v_u_39;
        end;
        local function f_cons() --[[ Name: cons ]] --[[ Line: 64 ]]
            --[[ Upvalues: (ref 1): v_u_30, (copy 2): p_u_27, (ref 3): v_u_31, (ref 4): v_u_32, (ref 5): v_u_35, (ref 6): v_u_33, (ref 7): v_u_34, (ref 8): v_u_36, (ref 9): v_u_38, (ref 10): v_u_37, (copy 11): p_u_28 ]]
            v_u_30 = p_u_27.MainSurface.SurfaceGui.Frame.Icon
            v_u_31 = p_u_27.MainSurface.SurfaceGui.Frame.IconOverlay
            pcall(function() --[[ Line: 67 ]]
                --[[ Upvalues: (ref 1): v_u_32, (ref 2): p_u_27 ]]
                v_u_32 = p_u_27.MainSurface.SurfaceGui.Frame.ColorSection
            end)
            pcall(function() --[[ Line: 70 ]]
                --[[ Upvalues: (ref 1): v_u_35, (ref 2): p_u_27 ]]
                v_u_35 = p_u_27.MainSurface.SurfaceGui.Frame.SongDifficultySection.Display
            end)
            v_u_33 = p_u_27.MainSurface.SurfaceGui.Frame.Background
            v_u_34 = p_u_27.MainSurface.SurfaceGui.Frame:FindFirstChild("VIPAccessDisplay")
            v_u_36 = p_u_27.MainSurface.SurfaceGui.Frame:FindFirstChild("NewDisplay")
            v_u_38 = p_u_27.MainSurface.SurfaceGui.Frame:FindFirstChild("FavoriteDisplay")
            v_u_37 = p_u_27.MainSurface.SurfaceGui.Frame:FindFirstChild("RankDisplay")
            if v_u_37 then
                v_u_37.Visible = false
            end;
            p_u_28:set_default_sgui()
        end;
        v29.layout = function(_) --[[ Name: layout ]] --[[ Line: 84 ]]
            --[[ Upvalues: (copy 1): p_u_28 ]]
            p_u_28:layout()
        end;
        local v_u_40 = true
        v29.set_visible = function(_, p41) --[[ Name: set_visible ]] --[[ Line: 89 ]]
            --[[ Upvalues: (ref 1): v_u_40, (copy 2): p_u_28 ]]
            v_u_40 = p41
            p_u_28:set_visible(p41)
        end;
        local v_u_42 = -1
        v29.display_song = function(_, p43) --[[ Name: display_song ]] --[[ Line: 95 ]]
            --[[ Upvalues: (ref 1): v_u_37, (ref 2): v_u_42, (copy 3): p_u_26, (ref 4): v_u_34, (ref 5): v_u_3, (ref 6): v_u_9, (ref 7): v_u_8, (ref 8): v_u_4, (ref 9): v_u_38, (ref 10): v_u_36, (ref 11): v_u_10, (ref 12): v_u_11, (ref 13): v_u_35, (ref 14): v_u_30, (ref 15): v_u_31, (ref 16): v_u_32, (ref 17): v_u_16, (ref 18): v_u_39 ]]
            if v_u_37 then
                v_u_37.Visible = false
                v_u_42 = -1
            end;
            local v44 = p_u_26._player_blob_manager:get_player_blob()
            if v_u_34 then
                if v_u_3:singleton():key_get_audiomod(p43) == v_u_9.Easy then
                    v_u_34.Visible = false
                elseif v_u_8:playerblob_has_vip_for_current_day(v44, p_u_26:get_current_dayid()) then
                    if v_u_4:get_song_key_owned_count(v44, p43) <= 0 and v_u_8:get_vip_songids_set():contains(p43) then
                        v_u_34.Visible = true
                    else
                        v_u_34.Visible = false
                    end;
                else
                    v_u_34.Visible = false
                end;
                if v_u_38 then
                    if v_u_34.Visible == false then
                        v_u_38.Visible = p_u_26._player_blob_manager:is_songkey_favorite(p43)
                    else
                        v_u_38.Visible = false
                    end;
                end;
            end;
            if v_u_36 then
                local v45 = v_u_36
                local v46 = v_u_10:songkey_is_new(p43)
                if v46 then
                    v46 = v_u_11.PlayUIShowNewSong == true
                end;
                v45.Visible = v46
            end;
            if v_u_35 then
                v_u_35.TextColor3 = v_u_3:singleton():get_difficulty_color_for_key(p43)
                v_u_35.Text = tostring(v_u_3:singleton():get_difficulty_for_key(p43))
            end;
            v_u_3:singleton():render_coverimage_for_key(v_u_30, v_u_31, p43)
            if v_u_32 then
                v_u_16:render_songkey_colorsection(p43, v_u_32)
            end;
            v_u_39 = p43
        end;
        local v_u_47 = false
        v29.set_selected = function(p48, p49) --[[ Name: set_selected ]] --[[ Line: 141 ]]
            --[[ Upvalues: (ref 1): v_u_47 ]]
            v_u_47 = p49
            return p48;
        end;
        v29.behaviour_update = function(_, _) --[[ Name: behaviour_update ]] --[[ Line: 143 ]]
            --[[ Upvalues: (ref 1): v_u_39, (ref 2): v_u_3, (ref 3): v_u_47, (ref 4): v_u_33, (ref 5): v_u_5, (ref 6): v_u_37, (ref 7): v_u_42, (copy 8): p_u_26, (ref 9): v_u_12 ]]
            if v_u_39 == v_u_3:invalid_songkey() or not v_u_47 then
                v_u_33.Image = v_u_5:get_play_options_song_container_assetid()
            else
                v_u_33.Image = v_u_5:get_play_options_song_container_selected_assetid()
            end;
            if v_u_37 and (v_u_3:singleton():contains_key(v_u_39) and v_u_42 ~= p_u_26._player_song_stats_manager:get_time_last_update()) then
                v_u_42 = p_u_26._player_song_stats_manager:get_time_last_update()
                local v50, v51 = p_u_26._player_song_stats_manager:get_best_grade_rank_value(v_u_39)
                if v51 > 0 then
                    v_u_37.Image = v_u_12:get_rank_value_icon(v50)
                    v_u_37.Visible = true
                    return;
                end;
                v_u_37.Visible = false
            end;
        end;
        f_cons()
        return v29;
    end
}
v_u_52.show_song_info_popup = function(_, p_u_53, p_u_54, p55, p56, p57, p58) --[[ Name: show_song_info_popup ]] --[[ Line: 166 ]]
    --[[ Upvalues: (ref 1): v_u_21, (copy 2): v_u_3, (copy 3): v_u_6, (copy 4): v_u_1, (copy 5): v_u_16, (copy 6): v_u_15, (copy 7): v_u_5, (copy 8): v_u_14, (copy 9): v_u_4, (copy 10): v_u_2, (ref 11): v_u_22, (copy 12): v_u_8, (ref 13): v_u_23, (copy 14): v_u_17, (ref 15): v_u_24, (copy 16): v_u_52 ]]
    local v_u_59 = p55 == nil and "" or p55
    local v_u_60 = p56 == nil and "" or p56
    local v_u_61 = p58 == nil and {} or p58
    p_u_53._menus:remove_menu_if(function(p62) --[[ Line: 179 ]]
        return p62.__type_key == "SongDisplayElement:show_song_info_popup";
    end)
    local v_u_63 = p_u_53._menus:push_menu(v_u_21:new(p_u_53, p_u_53._spui, p_u_53._menus))
    v_u_63.__type_key = "SongDisplayElement:show_song_info_popup"
    if p_u_54 == v_u_3:invalid_songkey() then
        v_u_6:warnf("SongDisplayElement:show_song_info_popup(%s) invalid songkey", (tostring(p_u_54)))
        return v_u_63;
    end;
    local v_u_64 = v_u_1:new()
    local function f_update_display() --[[ Name: update_display ]] --[[ Line: 192 ]]
        --[[ Upvalues: (ref 1): v_u_59, (ref 2): v_u_61, (ref 3): v_u_3, (copy 4): p_u_54, (ref 5): v_u_16, (ref 6): v_u_15, (ref 7): v_u_5, (copy 8): p_u_53, (ref 9): v_u_14, (ref 10): v_u_4, (ref 11): v_u_60, (copy 12): v_u_63, (copy 13): v_u_64 ]]
        local v65 = v_u_59
        if v_u_61.NoDefaultText ~= true then
            local v66 = (v65 .. string.format("<b>Artist</b>: %s\n", v_u_3:singleton():get_artist_for_key(p_u_54))) .. string.format("<b>Difficulty</b>: %d\n", v_u_3:singleton():get_difficulty_for_key(p_u_54))
            local v67 = v_u_16:songkey_get_color_list(p_u_54)
            local v68 = ""
            for v69 = 1, v67:count() do
                local v70 = v67:get(v69)
                if v69 ~= 1 then
                    if v69 ~= 2 then
                        break;
                    end;
                    v68 = v68 .. ", "
                end;
                v68 = v68 .. v_u_15:color_to_name(v70)
            end;
            v65 = (v66 .. string.format("<b>Elements</b>: %s\n", v68)) .. string.format("<b>Duration</b>: %s\n", v_u_5:format_ms_time(v_u_3:singleton():songkey_get_approx_length_sec(p_u_54) * 1000))
            if v_u_61.NoMiscSongInfo ~= true then
                local v71 = v65 .. string.format("<b>Note Count</b>: %s\n", v_u_5:comma_value(v_u_3:singleton():get_songkey_hit_count(p_u_54)))
                local v72 = v_u_3:singleton():songkey_get_average_bpm(p_u_54)
                if math.floor(v72) == v72 then
                    v65 = v71 .. string.format("<b>Average BPM</b>: %d\n", v72)
                else
                    v65 = v71 .. string.format("<b>Average BPM</b>: %.2f\n", v72)
                end;
            end;
            if v_u_61.NoCollectionInfo ~= true and v_u_3:singleton():get_songkey_should_grant(p_u_54) then
                local v73 = p_u_53._player_blob_manager:get_player_blob()
                v65 = (v65 .. string.format("<b>In Collection</b>: %s\n", (tostring(v_u_14:get_playerblob_songkey_in_collection(v73, p_u_54, p_u_53._player_blob_manager:get_cached_collection_info()))))) .. string.format("<b>Copies Owned</b>: %s\n", v_u_4:get_song_key_owned_count(v73, p_u_54))
            end;
            if v_u_61.NoDescription ~= true then
                v65 = v65 .. string.format("<b>Description</b>: %s", v_u_5:string_escape_richtext(v_u_3:singleton():get_description_for_key(p_u_54)))
            end;
        end;
        if #v_u_60 > 0 then
            v65 = v65 .. "\n"
        end;
        local v74 = v65 .. v_u_60
        local v75
        if v_u_61.TitleText == nil then
            v75 = string.format("Song: %s", v_u_3:singleton():get_title_for_key(p_u_54))
        else
            v75 = v_u_61.TitleText
        end;
        v_u_63:set_text(v75, v74, true)
        v_u_3:singleton():render_coverimage_for_key(v_u_63:get_image(), v_u_63:get_image_overlay(), p_u_54)
        for _, v76 in v_u_64:key_itr() do
            v76()
        end;
    end;
    local v_u_77 = p_u_53._bgm_manager:begin_preview_songkey(p_u_54)
    v_u_63:set_fn_on_remove(function() --[[ Line: 266 ]]
        --[[ Upvalues: (copy 1): p_u_53, (copy 2): v_u_77 ]]
        p_u_53._bgm_manager:stop_song_preview(v_u_77)
    end)
    if p57 == nil then
        local v_u_78 = v_u_63:get_action_buttons():pop_front()
        if v_u_78 then
            v_u_78:set_visible(true)
            for _, v79 in v_u_5:get_list_of_children_of_classname(v_u_78:get_part(), "TextLabel"):key_itr() do
                v79.Text = "Play"
            end;
            v_u_78:bind_data(function() --[[ Line: 304 ]]
                --[[ Upvalues: (copy 1): p_u_53, (ref 2): v_u_22, (copy 3): p_u_54 ]]
                p_u_53._menus:push_menu(v_u_22:new(p_u_53, p_u_53._spui, p_u_53._menus, p_u_54, nil))
            end)
            v_u_2:button_add_enabled_anim(v_u_78, function() --[[ Line: 310 ]]
                --[[ Upvalues: (copy 1): v_u_63 ]]
                return v_u_63:get_alpha();
            end)
            v_u_64:push_back(function() --[[ Line: 312 ]]
                --[[ Upvalues: (copy 1): p_u_53, (copy 2): v_u_78, (ref 3): v_u_8, (copy 4): p_u_54 ]]
                p_u_53._player_blob_manager:get_player_blob()
                v_u_78:set_enabled(v_u_8:playerblob_has_access_to_song(p_u_53._player_blob_manager:get_player_blob(), p_u_54, p_u_53._player_blob_manager:get_dayid(), p_u_53._player_blob_manager:get_cached_collection_info()))
            end)
        end;
        local v_u_80 = v_u_63:get_action_buttons():pop_front()
        if v_u_80 then
            v_u_80:set_visible(true)
            for _, v81 in v_u_5:get_list_of_children_of_classname(v_u_80:get_part(), "TextLabel"):key_itr() do
                v81.Text = "Craft"
            end;
            v_u_80:bind_data(function() --[[ Line: 333 ]]
                --[[ Upvalues: (copy 1): p_u_53, (ref 2): v_u_23, (copy 3): p_u_54, (copy 4): f_update_display ]]
                p_u_53._menus:push_menu(v_u_23:new(p_u_53, p_u_53._spui, p_u_53._menus, p_u_54, function() --[[ Line: 334 ]]
                    --[[ Upvalues: (ref 1): f_update_display ]]
                    f_update_display()
                end))
            end)
            v_u_2:button_add_enabled_anim(v_u_80, function() --[[ Line: 338 ]]
                --[[ Upvalues: (copy 1): v_u_63 ]]
                return v_u_63:get_alpha();
            end)
            v_u_64:push_back(function() --[[ Line: 340 ]]
                --[[ Upvalues: (copy 1): p_u_53, (ref 2): v_u_23, (copy 3): p_u_54, (copy 4): v_u_80, (ref 5): v_u_17 ]]
                local v82 = p_u_53._player_blob_manager:get_player_blob()
                local v83 = v_u_23:get_songkey_recipe_id(p_u_54)
                local v84 = v_u_80
                local v85
                if v83 == nil then
                    v85 = false
                else
                    v85 = v_u_17:can_craft_recipe(v82, v83)
                end;
                v84:set_enabled(v85)
            end)
        end;
        local v_u_86 = v_u_63:get_action_buttons():pop_front()
        if v_u_86 then
            v_u_86:set_visible(true)
            for _, v87 in v_u_5:get_list_of_children_of_classname(v_u_86:get_part(), "TextLabel"):key_itr() do
                v87.Text = "Editor"
            end;
            v_u_86:bind_data(function() --[[ Line: 355 ]]
                --[[ Upvalues: (ref 1): v_u_24, (copy 2): p_u_53, (copy 3): p_u_54 ]]
                v_u_24:show_published_map_list_ui_for_songkey(p_u_53, p_u_54)
            end)
            v_u_2:button_add_enabled_anim(v_u_86, function() --[[ Line: 358 ]]
                --[[ Upvalues: (copy 1): v_u_63 ]]
                return v_u_63:get_alpha();
            end)
            v_u_64:push_back(function() --[[ Line: 360 ]]
                --[[ Upvalues: (copy 1): v_u_86, (ref 2): v_u_24, (copy 3): p_u_54 ]]
                v_u_86:set_enabled(v_u_24:can_show_editor_menu_for_songkey(p_u_54))
            end)
        end;
        local v_u_88 = v_u_63:get_action_buttons():pop_front()
        if v_u_88 then
            v_u_88:set_visible(true)
            for _, v89 in v_u_5:get_list_of_children_of_classname(v_u_88:get_part(), "TextLabel"):key_itr() do
                v89.Text = "Top Scores"
            end;
            v_u_88:bind_data(function() --[[ Line: 373 ]]
                --[[ Upvalues: (ref 1): v_u_52, (copy 2): p_u_53, (copy 3): p_u_54 ]]
                v_u_52:show_top_scores_for_song(p_u_53, p_u_54)
            end)
            v_u_2:button_add_enabled_anim(v_u_88, function() --[[ Line: 376 ]]
                --[[ Upvalues: (copy 1): v_u_63 ]]
                return v_u_63:get_alpha();
            end)
            v_u_64:push_back(function() --[[ Line: 378 ]]
                --[[ Upvalues: (copy 1): v_u_88 ]]
                v_u_88:set_enabled(true)
            end)
        end;
        local v_u_90 = v_u_63:get_action_buttons():pop_front()
        if v_u_90 then
            v_u_90:set_visible(true)
            for _, v91 in v_u_5:get_list_of_children_of_classname(v_u_90:get_part(), "TextLabel"):key_itr() do
                v91.Text = "Recent Scores"
            end;
            v_u_90:bind_data(function() --[[ Line: 391 ]]
                --[[ Upvalues: (ref 1): v_u_52, (copy 2): p_u_53, (copy 3): p_u_54 ]]
                v_u_52:show_recent_scores_for_song(p_u_53, p_u_54)
            end)
            v_u_2:button_add_enabled_anim(v_u_90, function() --[[ Line: 394 ]]
                --[[ Upvalues: (copy 1): v_u_63 ]]
                return v_u_63:get_alpha();
            end)
            v_u_64:push_back(function() --[[ Line: 396 ]]
                --[[ Upvalues: (copy 1): v_u_90 ]]
                v_u_90:set_enabled(true)
            end)
        end;
    else
        for _, v92 in p57:key_itr() do
            local v93 = v_u_63:get_action_buttons():pop_front()
            if v93 then
                local v94, v_u_95, v_u_96 = v92(v_u_63, v93)
                v93:set_visible(true)
                for _, v97 in v_u_5:get_list_of_children_of_classname(v93:get_part(), "TextLabel"):key_itr() do
                    if v94 ~= nil then
                        v97.Text = v94
                    end;
                end;
                v93:bind_data(function() --[[ Line: 282 ]]
                    --[[ Upvalues: (copy 1): v_u_95, (copy 2): p_u_54 ]]
                    if v_u_95 ~= nil then
                        v_u_95(p_u_54)
                    end;
                end)
                v_u_2:button_add_enabled_anim(v93, function() --[[ Line: 287 ]]
                    --[[ Upvalues: (copy 1): v_u_63 ]]
                    return v_u_63:get_alpha();
                end)
                v_u_64:push_back(function() --[[ Line: 289 ]]
                    --[[ Upvalues: (copy 1): v_u_96 ]]
                    if v_u_96 ~= nil then
                        v_u_96()
                    end;
                end)
            end;
        end;
    end;
    f_update_display()
    return v_u_63;
end;
local function _(p_u_98, p99, p_u_100, p_u_101) --[[ Name: display_player_song_play_list_ui ]] --[[ Line: 407 ]]
    --[[ Upvalues: (copy 1): v_u_13, (ref 2): v_u_25, (copy 3): v_u_5, (copy 4): v_u_3, (copy 5): v_u_19, (copy 6): v_u_12 ]]
    local v_u_102 = v_u_13:loading_menu(p_u_98)
    p99(function(p_u_103) --[[ Line: 414 ]]
        --[[ Upvalues: (ref 1): v_u_13, (copy 2): p_u_98, (copy 3): v_u_102, (ref 4): v_u_25, (copy 5): p_u_100, (copy 6): p_u_101, (ref 7): v_u_5, (ref 8): v_u_3, (ref 9): v_u_19, (ref 10): v_u_12 ]]
        v_u_13:remove_loading_menu(p_u_98, v_u_102)
        p_u_98._menus:push_menu(v_u_25:new(p_u_98, p_u_98._spui, p_u_98._menus, function(p104) --[[ Line: 420 ]]
            --[[ Upvalues: (copy 1): p_u_103, (ref 2): p_u_100 ]]
            p104:get_element_list():push_back_from_list(p_u_103)
            p_u_100(p104)
        end, function(p105, _, _, _, p106, p107) --[[ Line: 424 ]]
            --[[ Upvalues: (ref 1): p_u_101 ]]
            p_u_101(p106, p105, p107)
            p106:set_select_button_enabled(true)
            p106:set_select_button_text("View")
        end, function(p108) --[[ Line: 429 ]]
            --[[ Upvalues: (ref 1): p_u_98, (ref 2): v_u_13, (ref 3): v_u_5, (ref 4): v_u_3, (ref 5): v_u_19, (ref 6): v_u_12 ]]
            if p108 ~= nil then
                p_u_98._menus:push_menu(v_u_13:new(p_u_98, p_u_98._spui, p_u_98._menus):set_rich_text("Play Info", string.format("<b>Song</b>: %s [<b>Difficulty</b>: %d]\n<b>Player</b>: %s [<b>ID</b>: %d]\n<b>Time</b>: %s\n<b>Mode</b>: %s\n<b>Accuracy</b>: %s%% (%s)\n<b>Score</b>: %s\n<b>Casual Mode Score</b>: %s\n<b>Gear Multiplier</b>: x%.2f\n<b>Gear Power</b>: %s", v_u_5:string_sub_max_len(v_u_3:singleton():get_title_for_key(p108:get_songkey()), 64), v_u_3:singleton():get_difficulty_for_key(p108:get_songkey()), p108:get_rbxname(), p108:get_rbxid(), p108:get_time_string(), v_u_5:enum_val_to_name(p108:get_match_mode(), v_u_19), p108:get_display_accuracy_string(), v_u_12:get_rank_value_name(v_u_12:accuracy_to_rank_value(p108:get_accuracy())), v_u_5:comma_value(p108:get_score()), v_u_5:comma_value(p108:get_naked_score()), p108:get_gear_multiplier(), v_u_5:comma_value(p108:get_gear_power()))))
            end;
        end)):set_close_on_element_select(false):get_list_adapter():set_do_wrap(true)
    end)
end;
local function f_display_list_element_title_shared(p109, p110, p111) --[[ Name: display_list_element_title_shared ]] --[[ Line: 459 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_19 ]]
    local v112 = string.format("[%.2f%%] Score: %s - %s", p110:get_display_accuracy_string(), v_u_5:comma_value(p110:get_score()), v_u_5:enum_val_to_name(p110:get_match_mode(), v_u_19))
    if p111 ~= nil then
        v112 = string.format("(%d) %s", p111, v112)
    end;
    p109:get_name_display().Text = v112
end;
v_u_52.show_top_scores_for_song = function(_, p_u_113, p_u_114) --[[ Name: show_top_scores_for_song ]] --[[ Line: 472 ]]
    --[[ Upvalues: (copy 1): v_u_7, (copy 2): v_u_18, (copy 3): v_u_3, (copy 4): v_u_5, (copy 5): f_display_list_element_title_shared, (copy 6): v_u_13, (ref 7): v_u_25, (copy 8): v_u_19, (copy 9): v_u_12 ]]
    local function v117(p_u_115) --[[ Line: 475 ]]
        --[[ Upvalues: (copy 1): p_u_113, (ref 2): v_u_7, (ref 3): v_u_18, (copy 4): p_u_114 ]]
        p_u_113._evt:wait_on_event_once(v_u_7.EVT_PlayerSongStats_ServerRequestPlayerSongPlayListResponse, function(p116) --[[ Line: 476 ]]
            --[[ Upvalues: (copy 1): p_u_115, (ref 2): v_u_18 ]]
            p_u_115(v_u_18:tab_to_list(p116))
        end)
        p_u_113._evt:fire_event_to_server(v_u_7.EVT_PlayerSongStats_ClientRequestPlayerSongPlayList, v_u_18.Category.TopScores, p_u_114)
    end;
    local function v_u_119(p118) --[[ Line: 481 ]]
        --[[ Upvalues: (ref 1): v_u_3, (copy 2): p_u_114 ]]
        p118:set_header_text("Top Scores")
        p118:set_sub_text(string.format("Song: %s", v_u_3:singleton():get_title_for_key(p_u_114)))
    end;
    local function v_u_124(p_u_120, p121, p122) --[[ Line: 485 ]]
        --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_display_list_element_title_shared ]]
        v_u_5:get_user_thumbnail(p121:get_rbxid(), function(p123, _) --[[ Line: 486 ]]
            --[[ Upvalues: (copy 1): p_u_120 ]]
            if p_u_120:get_icon_display() ~= nil then
                p_u_120:get_icon_display().Image = p123
            end;
        end, false)
        f_display_list_element_title_shared(p_u_120, p121, p122)
        p_u_120:get_description_display().Text = string.format("%s - Mult: x%.2f", p121:get_rbxname(), p121:get_gear_multiplier())
    end;
    local v_u_125 = v_u_13:loading_menu(p_u_113)
    v117(function(p_u_126) --[[ Line: 414 ]]
        --[[ Upvalues: (ref 1): v_u_13, (copy 2): p_u_113, (copy 3): v_u_125, (ref 4): v_u_25, (copy 5): v_u_119, (copy 6): v_u_124, (ref 7): v_u_5, (ref 8): v_u_3, (ref 9): v_u_19, (ref 10): v_u_12 ]]
        v_u_13:remove_loading_menu(p_u_113, v_u_125)
        p_u_113._menus:push_menu(v_u_25:new(p_u_113, p_u_113._spui, p_u_113._menus, function(p127) --[[ Line: 420 ]]
            --[[ Upvalues: (copy 1): p_u_126, (ref 2): v_u_119 ]]
            p127:get_element_list():push_back_from_list(p_u_126)
            v_u_119(p127)
        end, function(p128, _, _, _, p129, p130) --[[ Line: 424 ]]
            --[[ Upvalues: (ref 1): v_u_124 ]]
            v_u_124(p129, p128, p130)
            p129:set_select_button_enabled(true)
            p129:set_select_button_text("View")
        end, function(p131) --[[ Line: 429 ]]
            --[[ Upvalues: (ref 1): p_u_113, (ref 2): v_u_13, (ref 3): v_u_5, (ref 4): v_u_3, (ref 5): v_u_19, (ref 6): v_u_12 ]]
            if p131 ~= nil then
                p_u_113._menus:push_menu(v_u_13:new(p_u_113, p_u_113._spui, p_u_113._menus):set_rich_text("Play Info", string.format("<b>Song</b>: %s [<b>Difficulty</b>: %d]\n<b>Player</b>: %s [<b>ID</b>: %d]\n<b>Time</b>: %s\n<b>Mode</b>: %s\n<b>Accuracy</b>: %s%% (%s)\n<b>Score</b>: %s\n<b>Casual Mode Score</b>: %s\n<b>Gear Multiplier</b>: x%.2f\n<b>Gear Power</b>: %s", v_u_5:string_sub_max_len(v_u_3:singleton():get_title_for_key(p131:get_songkey()), 64), v_u_3:singleton():get_difficulty_for_key(p131:get_songkey()), p131:get_rbxname(), p131:get_rbxid(), p131:get_time_string(), v_u_5:enum_val_to_name(p131:get_match_mode(), v_u_19), p131:get_display_accuracy_string(), v_u_12:get_rank_value_name(v_u_12:accuracy_to_rank_value(p131:get_accuracy())), v_u_5:comma_value(p131:get_score()), v_u_5:comma_value(p131:get_naked_score()), p131:get_gear_multiplier(), v_u_5:comma_value(p131:get_gear_power()))))
            end;
        end)):set_close_on_element_select(false):get_list_adapter():set_do_wrap(true)
    end)
end;
v_u_52.show_recent_scores_for_song = function(_, p_u_132, p_u_133) --[[ Name: show_recent_scores_for_song ]] --[[ Line: 495 ]]
    --[[ Upvalues: (copy 1): v_u_7, (copy 2): v_u_18, (copy 3): v_u_3, (copy 4): v_u_5, (copy 5): f_display_list_element_title_shared, (copy 6): v_u_13, (ref 7): v_u_25, (copy 8): v_u_19, (copy 9): v_u_12 ]]
    local function v136(p_u_134) --[[ Line: 498 ]]
        --[[ Upvalues: (copy 1): p_u_132, (ref 2): v_u_7, (ref 3): v_u_18, (copy 4): p_u_133 ]]
        p_u_132._evt:wait_on_event_once(v_u_7.EVT_PlayerSongStats_ServerRequestPlayerSongPlayListResponse, function(p135) --[[ Line: 499 ]]
            --[[ Upvalues: (copy 1): p_u_134, (ref 2): v_u_18 ]]
            p_u_134(v_u_18:tab_to_list(p135))
        end)
        p_u_132._evt:fire_event_to_server(v_u_7.EVT_PlayerSongStats_ClientRequestPlayerSongPlayList, v_u_18.Category.RecentScores, p_u_133)
    end;
    local function v_u_138(p137) --[[ Line: 504 ]]
        --[[ Upvalues: (ref 1): v_u_3, (copy 2): p_u_133 ]]
        p137:set_header_text("Recent Scores")
        p137:set_sub_text(string.format("Song: %s", v_u_3:singleton():get_title_for_key(p_u_133)))
    end;
    local function v_u_142(p_u_139, p140) --[[ Line: 508 ]]
        --[[ Upvalues: (ref 1): v_u_5, (ref 2): f_display_list_element_title_shared ]]
        v_u_5:get_user_thumbnail(p140:get_rbxid(), function(p141, _) --[[ Line: 509 ]]
            --[[ Upvalues: (copy 1): p_u_139 ]]
            if p_u_139:get_icon_display() ~= nil then
                p_u_139:get_icon_display().Image = p141
            end;
        end, false)
        f_display_list_element_title_shared(p_u_139, p140)
        p_u_139:get_description_display().Text = string.format("%s @ %s", p140:get_rbxname(), p140:get_time_string())
    end;
    local v_u_143 = v_u_13:loading_menu(p_u_132)
    v136(function(p_u_144) --[[ Line: 414 ]]
        --[[ Upvalues: (ref 1): v_u_13, (copy 2): p_u_132, (copy 3): v_u_143, (ref 4): v_u_25, (copy 5): v_u_138, (copy 6): v_u_142, (ref 7): v_u_5, (ref 8): v_u_3, (ref 9): v_u_19, (ref 10): v_u_12 ]]
        v_u_13:remove_loading_menu(p_u_132, v_u_143)
        p_u_132._menus:push_menu(v_u_25:new(p_u_132, p_u_132._spui, p_u_132._menus, function(p145) --[[ Line: 420 ]]
            --[[ Upvalues: (copy 1): p_u_144, (ref 2): v_u_138 ]]
            p145:get_element_list():push_back_from_list(p_u_144)
            v_u_138(p145)
        end, function(p146, _, _, _, p147, p148) --[[ Line: 424 ]]
            --[[ Upvalues: (ref 1): v_u_142 ]]
            v_u_142(p147, p146, p148)
            p147:set_select_button_enabled(true)
            p147:set_select_button_text("View")
        end, function(p149) --[[ Line: 429 ]]
            --[[ Upvalues: (ref 1): p_u_132, (ref 2): v_u_13, (ref 3): v_u_5, (ref 4): v_u_3, (ref 5): v_u_19, (ref 6): v_u_12 ]]
            if p149 ~= nil then
                p_u_132._menus:push_menu(v_u_13:new(p_u_132, p_u_132._spui, p_u_132._menus):set_rich_text("Play Info", string.format("<b>Song</b>: %s [<b>Difficulty</b>: %d]\n<b>Player</b>: %s [<b>ID</b>: %d]\n<b>Time</b>: %s\n<b>Mode</b>: %s\n<b>Accuracy</b>: %s%% (%s)\n<b>Score</b>: %s\n<b>Casual Mode Score</b>: %s\n<b>Gear Multiplier</b>: x%.2f\n<b>Gear Power</b>: %s", v_u_5:string_sub_max_len(v_u_3:singleton():get_title_for_key(p149:get_songkey()), 64), v_u_3:singleton():get_difficulty_for_key(p149:get_songkey()), p149:get_rbxname(), p149:get_rbxid(), p149:get_time_string(), v_u_5:enum_val_to_name(p149:get_match_mode(), v_u_19), p149:get_display_accuracy_string(), v_u_12:get_rank_value_name(v_u_12:accuracy_to_rank_value(p149:get_accuracy())), v_u_5:comma_value(p149:get_score()), v_u_5:comma_value(p149:get_naked_score()), p149:get_gear_multiplier(), v_u_5:comma_value(p149:get_gear_power()))))
            end;
        end)):set_close_on_element_select(false):get_list_adapter():set_do_wrap(true)
    end)
end;
v_u_52.show_recent_scores_for_player = function(_, p_u_150) --[[ Name: show_recent_scores_for_player ]] --[[ Line: 518 ]]
    --[[ Upvalues: (copy 1): v_u_7, (copy 2): v_u_18, (copy 3): v_u_3, (copy 4): f_display_list_element_title_shared, (copy 5): v_u_5, (copy 6): v_u_13, (ref 7): v_u_25, (copy 8): v_u_19, (copy 9): v_u_12 ]]
    local function v153(p_u_151) --[[ Line: 521 ]]
        --[[ Upvalues: (copy 1): p_u_150, (ref 2): v_u_7, (ref 3): v_u_18 ]]
        p_u_150._evt:wait_on_event_once(v_u_7.EVT_PlayerSongStats_ServerRequestPlayerSongPlayListResponse, function(p152) --[[ Line: 522 ]]
            --[[ Upvalues: (copy 1): p_u_151, (ref 2): v_u_18 ]]
            p_u_151(v_u_18:tab_to_list(p152))
        end)
        p_u_150._evt:fire_event_to_server(v_u_7.EVT_PlayerSongStats_ClientRequestPlayerSongPlayList, v_u_18.Category.PlayerRecentScores, 0)
    end;
    local function v_u_155(p154) --[[ Line: 527 ]]
        p154:set_header_text("Your Recent Scores")
    end;
    local function v_u_158(p156, p157) --[[ Line: 530 ]]
        --[[ Upvalues: (ref 1): v_u_3, (ref 2): f_display_list_element_title_shared, (ref 3): v_u_5 ]]
        p156:get_icon_display().Image = v_u_3:singleton():get_coverimage_assetid_for_key(p157:get_songkey())
        f_display_list_element_title_shared(p156, p157)
        p156:get_description_display().Text = string.format("%s - %s [%d]", p157:get_time_string(), v_u_5:string_sub_max_len(v_u_3:singleton():get_title_for_key(p157:get_songkey()), 32), v_u_3:singleton():get_difficulty_for_key(p157:get_songkey()))
    end;
    local v_u_159 = v_u_13:loading_menu(p_u_150)
    v153(function(p_u_160) --[[ Line: 414 ]]
        --[[ Upvalues: (ref 1): v_u_13, (copy 2): p_u_150, (copy 3): v_u_159, (ref 4): v_u_25, (copy 5): v_u_155, (copy 6): v_u_158, (ref 7): v_u_5, (ref 8): v_u_3, (ref 9): v_u_19, (ref 10): v_u_12 ]]
        v_u_13:remove_loading_menu(p_u_150, v_u_159)
        p_u_150._menus:push_menu(v_u_25:new(p_u_150, p_u_150._spui, p_u_150._menus, function(p161) --[[ Line: 420 ]]
            --[[ Upvalues: (copy 1): p_u_160, (ref 2): v_u_155 ]]
            p161:get_element_list():push_back_from_list(p_u_160)
            v_u_155(p161)
        end, function(p162, _, _, _, p163, p164) --[[ Line: 424 ]]
            --[[ Upvalues: (ref 1): v_u_158 ]]
            v_u_158(p163, p162, p164)
            p163:set_select_button_enabled(true)
            p163:set_select_button_text("View")
        end, function(p165) --[[ Line: 429 ]]
            --[[ Upvalues: (ref 1): p_u_150, (ref 2): v_u_13, (ref 3): v_u_5, (ref 4): v_u_3, (ref 5): v_u_19, (ref 6): v_u_12 ]]
            if p165 ~= nil then
                p_u_150._menus:push_menu(v_u_13:new(p_u_150, p_u_150._spui, p_u_150._menus):set_rich_text("Play Info", string.format("<b>Song</b>: %s [<b>Difficulty</b>: %d]\n<b>Player</b>: %s [<b>ID</b>: %d]\n<b>Time</b>: %s\n<b>Mode</b>: %s\n<b>Accuracy</b>: %s%% (%s)\n<b>Score</b>: %s\n<b>Casual Mode Score</b>: %s\n<b>Gear Multiplier</b>: x%.2f\n<b>Gear Power</b>: %s", v_u_5:string_sub_max_len(v_u_3:singleton():get_title_for_key(p165:get_songkey()), 64), v_u_3:singleton():get_difficulty_for_key(p165:get_songkey()), p165:get_rbxname(), p165:get_rbxid(), p165:get_time_string(), v_u_5:enum_val_to_name(p165:get_match_mode(), v_u_19), p165:get_display_accuracy_string(), v_u_12:get_rank_value_name(v_u_12:accuracy_to_rank_value(p165:get_accuracy())), v_u_5:comma_value(p165:get_score()), v_u_5:comma_value(p165:get_naked_score()), p165:get_gear_multiplier(), v_u_5:comma_value(p165:get_gear_power()))))
            end;
        end)):set_close_on_element_select(false):get_list_adapter():set_do_wrap(true)
    end)
end;
return v_u_52;
