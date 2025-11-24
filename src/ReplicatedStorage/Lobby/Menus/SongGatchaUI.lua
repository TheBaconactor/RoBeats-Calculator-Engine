-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:43 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_4 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_6 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_7 = require(game.ReplicatedStorage.Menu.SPUIButton)
local v_u_8 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
require(game.ReplicatedStorage.Shared.SPVector)
local v_u_9 = require(game.ReplicatedStorage.Local.DebugOut)
require(game.ReplicatedStorage.Shared.InputUtil)
require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_10 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.PlayerInfo.PurchaseInfo)
local v_u_11 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_12 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_13 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_14 = require(game.ReplicatedStorage.PlayerInfo.SongGatchaUtil)
local v_u_15 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_16 = require(game.ReplicatedStorage.LocalShared.PurchaseRedirect)
local v_u_17 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
local v_u_18 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_19 = require(game.ReplicatedStorage.Lobby.Menus.SongsAcquiredUI)
local v20 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_21 = nil
local v_u_22 = nil
v20:require_client(function() --[[ Line: 31 ]]
    --[[ Upvalues: (ref 1): v_u_21, (ref 2): v_u_22 ]]
    v_u_21 = require(game.ReplicatedStorage.Lobby.Menus.RewardDescriptionInfoAcquiredUI)
    v_u_22 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
end)
local v_u_23 = {
    ["Mode"] = {
        ["Closed"] = 1,
        ["InfoRequest"] = 2,
        ["Ready"] = 3
    }
}
local v_u_24 = v_u_3:new():push_back_table_list({
    v_u_14.Tiers.Tier0,
    v_u_14.Tiers.Tier1,
    v_u_14.Tiers.Tier2,
    v_u_14.Tiers.Tier3,
    v_u_14.Tiers.Tier4
})
local v_u_25 = v_u_2:new()
local function f_list_indexed_random(p26, p27) --[[ Name: list_indexed_random ]] --[[ Line: 53 ]]
    --[[ Upvalues: (copy 1): v_u_25, (copy 2): v_u_1 ]]
    if v_u_25:get(p27) == nil then
        v_u_25:add(p27, v_u_1:rand_rangei(0, 9999))
    end;
    return p26:get(v_u_25:get(p27) % p26:count() + 1);
end;
local v_u_28 = 1
local v_u_29 = 1
local function f_get_current_song_gatcha_tier() --[[ Name: get_current_song_gatcha_tier ]] --[[ Line: 62 ]]
    --[[ Upvalues: (copy 1): v_u_24, (ref 2): v_u_28 ]]
    return v_u_24:get(v_u_28);
end;
v_u_23.new = function(_, p_u_30, p_u_31, p_u_32) --[[ Name: new ]] --[[ Line: 64 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_23, (copy 3): v_u_3, (copy 4): v_u_1, (copy 5): v_u_11, (copy 6): v_u_7, (copy 7): v_u_12, (copy 8): v_u_17, (ref 9): v_u_29, (copy 10): v_u_6, (copy 11): v_u_5, (ref 12): v_u_28, (copy 13): v_u_24, (copy 14): v_u_9, (copy 15): v_u_14, (copy 16): f_get_current_song_gatcha_tier, (copy 17): v_u_15, (copy 18): f_list_indexed_random, (copy 19): v_u_13, (copy 20): v_u_8, (copy 21): v_u_2, (copy 22): v_u_10, (copy 23): v_u_18, (ref 24): v_u_22, (ref 25): v_u_21, (copy 26): v_u_19, (copy 27): v_u_16 ]]
    local v_u_33 = v_u_4:new(p_u_31, p_u_32)
    local v_u_34 = nil
    local l__shop_local_protocol_0 = p_u_30._shop_local_protocol
    local l_InfoRequest_0 = v_u_23.Mode.InfoRequest
    local function _() --[[ Name: request_response_kill ]] --[[ Line: 72 ]]
        --[[ Upvalues: (ref 1): l_InfoRequest_0, (ref 2): v_u_23 ]]
        return l_InfoRequest_0 == v_u_23.Mode.Closed;
    end;
    local v_u_35 = 1
    local v_u_36 = 1
    local v_u_37 = nil
    local v_u_38 = nil
    local v_u_39 = nil
    local v_u_40 = nil
    local v_u_41 = nil
    local v_u_42 = nil
    local v_u_43 = nil
    local v_u_44 = nil
    local v_u_45 = nil
    local v_u_46 = nil
    local v_u_47 = nil
    local v_u_48 = nil
    local v_u_49 = nil
    local v_u_50 = v_u_3:new()
    local function f_cons() --[[ Name: cons ]] --[[ Line: 89 ]]
        --[[ Upvalues: (ref 1): v_u_34, (ref 2): v_u_1, (ref 3): v_u_11, (copy 4): v_u_33, (ref 5): v_u_37, (ref 6): v_u_7, (copy 7): p_u_31, (copy 8): p_u_30, (ref 9): v_u_12, (ref 10): l_InfoRequest_0, (ref 11): v_u_23, (copy 12): p_u_32, (ref 13): v_u_17, (ref 14): v_u_42, (ref 15): v_u_29, (ref 16): v_u_43, (ref 17): v_u_38, (ref 18): v_u_39, (ref 19): v_u_40, (ref 20): v_u_41, (ref 21): v_u_44, (ref 22): v_u_45, (ref 23): v_u_46, (ref 24): v_u_47, (ref 25): v_u_6, (ref 26): v_u_5, (ref 27): v_u_28, (ref 28): v_u_24, (ref 29): v_u_48, (ref 30): v_u_49, (copy 31): v_u_50, (copy 32): l__shop_local_protocol_0 ]]
        v_u_34 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.SongGatchaUI:Clone()
        v_u_34.Name = v_u_1:gen_name(v_u_34.Name)
        v_u_34.Parent = v_u_11:get_world_ui_folder()
        v_u_33._native_size = v_u_34.PrimaryPart.Size
        v_u_33._size = v_u_33._native_size
        v_u_37 = v_u_7:new(v_u_34.RollButtonSurface, p_u_31, function() --[[ Line: 99 ]]
            --[[ Upvalues: (ref 1): p_u_30, (ref 2): v_u_12, (ref 3): v_u_33 ]]
            p_u_30._sfx_manager:play_sfx(v_u_12.SFX_MENU_OPEN_LONG)
            v_u_33:do_gatcha_roll()
        end)
        v_u_37:set_position_nxy(0.5, 0.5)
        v_u_37:set_anchor_rnxy(0.5, 0.5)
        v_u_37:set_passive_anim()
        v_u_33:add_cycle_element(p_u_30, 1, v_u_37)
        local v_u_51 = v_u_7:new(v_u_34.BackButtonSurface, p_u_31, function() --[[ Line: 113 ]]
            --[[ Upvalues: (ref 1): p_u_30, (ref 2): v_u_12, (ref 3): l_InfoRequest_0, (ref 4): v_u_23, (ref 5): v_u_33, (ref 6): p_u_32 ]]
            p_u_30._sfx_manager:play_sfx(v_u_12.SFX_MENU_CLOSE)
            l_InfoRequest_0 = v_u_23.Mode.Closed
            v_u_33:reset_starmachine_npc()
            p_u_32:remove_menu(v_u_33)
        end)
        v_u_51:set_position_nxy(0.95, 0.05)
        v_u_51:set_anchor_rnxy(0.5, 0.5)
        v_u_51:set_pre_layout_fn(function() --[[ Line: 122 ]]
            --[[ Upvalues: (copy 1): v_u_51 ]]
            local v52 = v_u_51:get_native_size()
            v_u_51:set_position_offset_xy(-v52.X * 0.5, -v52.Y * 0.5)
        end)
        v_u_33:add_cycle_element(p_u_30, 1, v_u_51)
        v_u_33:set_alpha(0)
        p_u_30._npcs:try_get_npc(v_u_17.NPC.NPC_StarMachine, function(p53) --[[ Line: 132 ]]
            p53:stop_anim()
        end)
        v_u_42 = v_u_33:add_cycle_element(p_u_30, 1, v_u_7:new(v_u_34.LeftArrowSurface, p_u_31, function() --[[ Line: 141 ]]
            --[[ Upvalues: (ref 1): p_u_30, (ref 2): v_u_12, (ref 3): v_u_29, (ref 4): v_u_33 ]]
            p_u_30._sfx_manager:play_sfx(v_u_12.SFX_BUTTONPRESS)
            v_u_29 = v_u_29 - 1
            v_u_33:update_selected_gatcha(true, false)
        end):set_position_nxy(0.5, 0.5):set_anchor_rnxy(0.5, 0.5):set_position_offset_xy(-2, 0))
        v_u_43 = v_u_33:add_cycle_element(p_u_30, 1, v_u_7:new(v_u_34.RightArrowSurface, p_u_31, function() --[[ Line: 156 ]]
            --[[ Upvalues: (ref 1): p_u_30, (ref 2): v_u_12, (ref 3): v_u_29, (ref 4): v_u_33 ]]
            p_u_30._sfx_manager:play_sfx(v_u_12.SFX_BUTTONPRESS)
            v_u_29 = v_u_29 + 1
            v_u_33:update_selected_gatcha(true, false)
        end):set_position_nxy(0.5, 0.5):set_anchor_rnxy(0.5, 0.5):set_position_offset_xy(2, 0))
        p_u_30:set_character_random_position_around_anchors_fn(function() --[[ Line: 167 ]]
            --[[ Upvalues: (ref 1): v_u_11 ]]
            return v_u_11:get_lobby_anchors().Shop.Gatcha.StandAnchor, v_u_11:get_lobby_anchors().Shop.Gatcha.LookAnchor, 1.5, 4;
        end)
        p_u_30:transition_local_camera_to_anchors_fn(function() --[[ Line: 173 ]]
            --[[ Upvalues: (ref 1): v_u_11 ]]
            return v_u_11:get_lobby_anchors().Shop.Gatcha.CameraAnchor, v_u_11:get_lobby_anchors().Shop.Gatcha.LookAnchor;
        end)
        v_u_38 = v_u_34.MainSurface.SurfaceGui.Frame.StarSection.Display
        v_u_39 = v_u_34.RollButtonSurface.Part.SurfaceGui.Frame.PriceDisplay
        v_u_40 = v_u_34.RollButtonSurface.Part.SurfaceGui.Frame.CountDisplay
        v_u_41 = v_u_34.RollButtonSurface.Part.SurfaceGui.Frame.BonusDisplay
        v_u_44 = v_u_34.MainSurface.SurfaceGui.Frame.SongDifficultyRangeDisplay
        v_u_45 = v_u_34.MainSurface.SurfaceGui.Frame.NewSongProbDisplay
        v_u_46 = v_u_34.MainSurface.SurfaceGui.Frame.NewHardModeProbDisplay
        v_u_47 = v_u_33:add_cycle_element(p_u_30, 1, v_u_6:new(v_u_5:new(v_u_33, v_u_34.PrimaryPart, v_u_34.TierLeftArrow), p_u_31, function() --[[ Line: 190 ]]
            --[[ Upvalues: (ref 1): p_u_30, (ref 2): v_u_12, (ref 3): v_u_28, (ref 4): v_u_24, (ref 5): v_u_33 ]]
            p_u_30._sfx_manager:play_sfx(v_u_12.SFX_BUTTONPRESS)
            v_u_28 = v_u_28 - 1
            if v_u_28 <= 0 then
                v_u_28 = v_u_24:count()
            end;
            v_u_33:update_selected_gatcha(false, true)
        end):set_passive_anim())
        v_u_48 = v_u_33:add_cycle_element(p_u_30, 1, v_u_6:new(v_u_5:new(v_u_33, v_u_34.PrimaryPart, v_u_34.TierRightArrow), p_u_31, function() --[[ Line: 203 ]]
            --[[ Upvalues: (ref 1): p_u_30, (ref 2): v_u_12, (ref 3): v_u_28, (ref 4): v_u_24, (ref 5): v_u_33 ]]
            p_u_30._sfx_manager:play_sfx(v_u_12.SFX_BUTTONPRESS)
            v_u_28 = v_u_28 + 1
            if v_u_28 > v_u_24:count() then
                v_u_28 = 1
            end;
            v_u_33:update_selected_gatcha(false, true)
        end):set_passive_anim())
        v_u_49 = v_u_34.MainSurface.SurfaceGui
        v_u_50:push_back_table_list({
            v_u_34.MainSurface.SurfaceGui.Frame.DemoSongSection1,
            v_u_34.MainSurface.SurfaceGui.Frame.DemoSongSection2,
            v_u_34.MainSurface.SurfaceGui.Frame.DemoSongSection3,
            v_u_34.MainSurface.SurfaceGui.Frame.DemoSongSection4,
            v_u_34.MainSurface.SurfaceGui.Frame.DemoSongSection5,
            v_u_34.MainSurface.SurfaceGui.Frame.DemoSongSection6
        })
        v_u_33:update_blob_sync()
        l_InfoRequest_0 = v_u_23.Mode.InfoRequest
        v_u_33:update_ui_mode()
        l__shop_local_protocol_0:request_gatcha_info(function(p54) --[[ Line: 229 ]]
            --[[ Upvalues: (ref 1): l_InfoRequest_0, (ref 2): v_u_23, (ref 3): v_u_33 ]]
            if l_InfoRequest_0 ~= v_u_23.Mode.Closed then
                l_InfoRequest_0 = v_u_23.Mode.Ready
                v_u_33:update_ui_mode()
                v_u_33:info_update(p54)
            end;
        end)
    end;
    local v_u_55 = {}
    v_u_33.info_update = function(p56, p57) --[[ Name: info_update ]] --[[ Line: 244 ]]
        --[[ Upvalues: (ref 1): v_u_55 ]]
        v_u_55 = p57
        p56:update_selected_gatcha(true, true)
    end;
    v_u_33.update_selected_gatcha = function(_, p58, p59) --[[ Name: update_selected_gatcha ]] --[[ Line: 249 ]]
        --[[ Upvalues: (ref 1): v_u_29, (ref 2): v_u_55, (ref 3): v_u_9, (ref 4): v_u_39, (ref 5): v_u_40, (ref 6): v_u_41, (ref 7): v_u_42, (ref 8): v_u_43, (ref 9): v_u_44, (ref 10): v_u_14, (ref 11): f_get_current_song_gatcha_tier, (copy 12): p_u_30, (ref 13): v_u_24, (ref 14): v_u_28, (ref 15): v_u_45, (ref 16): v_u_46, (copy 17): v_u_50, (ref 18): v_u_1, (ref 19): v_u_15, (ref 20): f_list_indexed_random ]]
        if p58 then
            if v_u_29 > #v_u_55 or v_u_29 < 1 then
                return v_u_9:warnf("updated_selected_gatcha(%d)", v_u_29);
            end;
            local v60 = v_u_55[v_u_29]
            v_u_39.Text = string.format("%d", v60.Cost)
            v_u_40.Text = string.format("x%d", v60.Count)
            if v60.Bonus > 0 then
                v_u_41.Text = string.format("+%d Bonus!", v60.Bonus)
            else
                v_u_41.Text = ""
            end;
            v_u_42:set_visible(v_u_29 > 1)
            v_u_43:set_visible(v_u_29 < #v_u_55)
        end;
        if p59 then
            v_u_44.Text = v_u_14:tier_get_desc(f_get_current_song_gatcha_tier())
            local v61, v62 = v_u_14:playerblob_get_tier_new_song_new_hardmode_d100(p_u_30._player_blob_manager:get_player_blob(), v_u_24:get(v_u_28), p_u_30._player_blob_manager:get_cached_collection_info())
            v_u_45.Text = string.format("%.2f%%", v61)
            v_u_46.Text = string.format("%.2f%%", v62)
            local v63, v64 = v_u_14:tier_get_available_normal_hard_songs(f_get_current_song_gatcha_tier())
            for v65 = 1, v_u_50:count() do
                local v66 = v_u_50:get(v65)
                if v64:count() > 0 and v_u_1:rand_rangef(0, 100) < v_u_14:tier_get_hardmode_roll_percentage_d100(f_get_current_song_gatcha_tier()) then
                    v_u_15:singleton():render_coverimage_for_key(v66.AlbumArt, v66.AlbumArtOverlay, f_list_indexed_random(v64, v65))
                else
                    v_u_15:singleton():render_coverimage_for_key(v66.AlbumArt, v66.AlbumArtOverlay, f_list_indexed_random(v63, v65))
                end;
            end;
        end;
    end;
    v_u_33.update_ui_mode = function(_) --[[ Name: update_ui_mode ]] --[[ Line: 285 ]]
        --[[ Upvalues: (ref 1): l_InfoRequest_0, (ref 2): v_u_23, (ref 3): v_u_37, (ref 4): v_u_42, (ref 5): v_u_43, (ref 6): v_u_47, (ref 7): v_u_48, (ref 8): v_u_49 ]]
        if l_InfoRequest_0 == v_u_23.Mode.InfoRequest then
            v_u_37:set_visible(false)
            v_u_42:set_visible(false)
            v_u_43:set_visible(false)
            v_u_47:set_visible(false)
            v_u_48:set_visible(false)
            v_u_49.Enabled = false
        else
            v_u_37:set_visible(true)
            v_u_42:set_visible(true)
            v_u_43:set_visible(true)
            v_u_47:set_visible(true)
            v_u_48:set_visible(true)
            v_u_49.Enabled = true
        end;
    end;
    v_u_33.do_gatcha_roll = function(p_u_67) --[[ Name: do_gatcha_roll ]] --[[ Line: 303 ]]
        --[[ Upvalues: (ref 1): v_u_55, (ref 2): v_u_29, (ref 3): v_u_13, (copy 4): p_u_32, (ref 5): v_u_8, (copy 6): p_u_30, (copy 7): p_u_31, (copy 8): l__shop_local_protocol_0, (ref 9): v_u_24, (ref 10): v_u_28, (ref 11): v_u_2, (ref 12): v_u_10, (ref 13): v_u_18, (ref 14): v_u_3, (ref 15): v_u_22, (ref 16): v_u_21, (ref 17): v_u_19, (ref 18): v_u_16 ]]
        local v68 = v_u_55[v_u_29]
        v_u_13:is_non_nil(v68)
        local l_ID_0 = v68.ID
        v_u_13:is_int(l_ID_0)
        v_u_13:is_int_greater_than(v68.Cost, 0)
        local function f_do_purchase() --[[ Name: do_purchase ]] --[[ Line: 310 ]]
            --[[ Upvalues: (ref 1): p_u_32, (ref 2): v_u_8, (ref 3): p_u_30, (ref 4): p_u_31, (ref 5): l__shop_local_protocol_0, (copy 6): l_ID_0, (ref 7): v_u_24, (ref 8): v_u_28, (ref 9): v_u_2, (ref 10): v_u_10, (copy 11): p_u_67, (ref 12): v_u_18, (ref 13): v_u_3, (ref 14): v_u_22, (ref 15): v_u_21, (ref 16): v_u_19 ]]
            local v_u_69 = p_u_32:push_menu(v_u_8:new(p_u_30, p_u_31, p_u_32):set_text("Purchasing...", ""):set_close_button_visible(false))
            l__shop_local_protocol_0:try_purchase_gatcha(l_ID_0, v_u_24:get(v_u_28), function(p70, p_u_71, p72) --[[ Line: 312 ]]
                --[[ Upvalues: (ref 1): p_u_32, (copy 2): v_u_69, (ref 3): v_u_8, (ref 4): p_u_30, (ref 5): p_u_31, (ref 6): v_u_2, (ref 7): v_u_10, (ref 8): p_u_67, (ref 9): v_u_18, (ref 10): v_u_3, (ref 11): v_u_22, (ref 12): v_u_21, (ref 13): v_u_19 ]]
                if p70 == false or (p_u_71 == nil or #p_u_71 == 0) then
                    p_u_32:remove_menu(v_u_69)
                    p_u_32:push_menu(v_u_8:new(p_u_30, p_u_31, p_u_32):set_text("Purchase Failed", p72))
                else
                    local v73 = p_u_30._player_blob_manager:get_player_blob()
                    local v_u_74 = v_u_2:new()
                    for v75 = 1, #p_u_71 do
                        local v76 = p_u_71[v75]
                        if v_u_10:get_song_key_owned_count_including_collection(v73, v76, p_u_30._player_blob_manager:get_cached_collection_info()) == 0 then
                            p_u_30._player_blob_manager:add_recently_acquired_songid(v76)
                            v_u_74:add(v76, true)
                        end;
                    end;
                    p_u_30._player_blob_manager:do_sync(function(_) --[[ Line: 333 ]]
                        --[[ Upvalues: (ref 1): p_u_67, (ref 2): p_u_32, (ref 3): v_u_69, (ref 4): v_u_18, (ref 5): v_u_3, (copy 6): p_u_71, (ref 7): v_u_22, (ref 8): v_u_21, (ref 9): p_u_30, (ref 10): p_u_31, (ref 11): v_u_19, (copy 12): v_u_74 ]]
                        p_u_67:update_selected_gatcha(false, true)
                        p_u_32:remove_menu(v_u_69)
                        if v_u_18.UseRewardDescriptionInfoAcquiredUI == true then
                            local v77 = v_u_3:new()
                            for v78 = 1, #p_u_71 do
                                v77:push_back(v_u_22.RewardInfo:new(v_u_22.RewardType.Song, 1, p_u_71[v78]))
                            end;
                            p_u_32:push_menu(v_u_21:new(p_u_30, p_u_31, p_u_32, v77):set_header_text("Songs Acquired!"):set_sub_text("Acquired the following songs from the Song Machine..."))
                        else
                            p_u_32:push_menu(v_u_19:new(p_u_30, p_u_31, p_u_32, p_u_71, v_u_74))
                        end;
                    end)
                end;
            end)
        end;
        local v79 = v_u_16:playerblob_purchase_needs_redirect(p_u_30._player_blob_manager:get_player_blob(), v_u_10.CurrencyType.Stars, v68.Cost)
        if v79:is_valid() then
            v_u_16:show_purchase_redirect(p_u_30, v79, function(p80) --[[ Line: 357 ]]
                --[[ Upvalues: (copy 1): f_do_purchase ]]
                if p80 then
                    f_do_purchase()
                end;
            end)
        else
            f_do_purchase()
        end;
    end;
    local v_u_81 = -1
    v_u_33.update_blob_sync = function(_) --[[ Name: update_blob_sync ]] --[[ Line: 368 ]]
        --[[ Upvalues: (copy 1): p_u_30, (ref 2): v_u_81, (ref 3): v_u_38 ]]
        if p_u_30._player_blob_manager:is_synced() and p_u_30._player_blob_manager:get_synced_time() ~= v_u_81 then
            v_u_81 = p_u_30._player_blob_manager:get_synced_time()
            v_u_38.Text = string.format("%d", p_u_30._player_blob_manager:get_player_blob().StarCurrency)
        end;
    end;
    local v_u_82 = false
    v_u_33.visual_update = function(p83, p84, p85) --[[ Name: visual_update ]] --[[ Line: 378 ]]
        --[[ Upvalues: (copy 1): p_u_30, (ref 2): v_u_82, (ref 3): v_u_17 ]]
        if p_u_30:transition_local_camera_cframe_finished() ~= false then
            if v_u_82 == false then
                v_u_82 = true
                p_u_30._npcs:try_get_npc(v_u_17.NPC.NPC_StarMachine, function(p86) --[[ Line: 385 ]]
                    p86:show_fade_back(true)
                    p86:show_face_machine_selected()
                end)
            end;
            p83:visual_update_base(p84, p85)
        end;
    end;
    v_u_33.behaviour_update = function(p87, p88, p89) --[[ Name: behaviour_update ]] --[[ Line: 394 ]]
        p87:behaviour_update_base(p88, p89)
        p87:update_blob_sync()
    end;
    v_u_33.layout = function(p90) --[[ Name: layout ]] --[[ Line: 400 ]]
        --[[ Upvalues: (copy 1): p_u_31, (ref 2): v_u_36, (ref 3): v_u_34 ]]
        p_u_31:uiobj_rescale_to_max_nxy(p90, 0.5, 0.3, v_u_36)
        v_u_34:SetPrimaryPartCFrame(p_u_31:get_cframe({
            ["PositionNXY"] = Vector2.new(0.025, 0.95),
            ["OffsetXYZ"] = p90:anchored_offset(0, 1),
            ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
        }))
    end;
    v_u_33.reset_starmachine_npc = function(_) --[[ Name: reset_starmachine_npc ]] --[[ Line: 409 ]]
        --[[ Upvalues: (copy 1): p_u_30, (ref 2): v_u_17 ]]
        p_u_30._npcs:try_get_npc(v_u_17.NPC.NPC_StarMachine, function(p91) --[[ Line: 410 ]]
            p91:show_fade_back(false)
            p91:play_idle_anim()
            p91:show_face_neutral()
        end)
    end;
    v_u_33.do_remove = function(p92, _) --[[ Name: do_remove ]] --[[ Line: 417 ]]
        --[[ Upvalues: (ref 1): v_u_34 ]]
        p92:reset_starmachine_npc()
        v_u_34:Destroy()
    end;
    v_u_33.set_alpha = function(_, p93) --[[ Name: set_alpha ]] --[[ Line: 422 ]]
        --[[ Upvalues: (ref 1): v_u_35, (ref 2): v_u_1, (ref 3): v_u_34 ]]
        if v_u_35 ~= p93 then
            v_u_35 = p93
            v_u_1:r_set_alpha(v_u_34, v_u_35)
        end;
    end;
    v_u_33.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 428 ]]
        --[[ Upvalues: (ref 1): v_u_35 ]]
        return v_u_35;
    end;
    v_u_33.set_scale = function(_, p94) --[[ Name: set_scale ]] --[[ Line: 429 ]]
        --[[ Upvalues: (ref 1): v_u_36 ]]
        v_u_36 = p94
    end;
    v_u_33.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 430 ]]
        --[[ Upvalues: (ref 1): v_u_36 ]]
        return v_u_36;
    end;
    v_u_33.get_native_size = function(p95) --[[ Name: get_native_size ]] --[[ Line: 432 ]]
        return p95._native_size;
    end;
    v_u_33.get_size = function(p96) --[[ Name: get_size ]] --[[ Line: 435 ]]
        return p96._size;
    end;
    v_u_33.set_size = function(p97, p98) --[[ Name: set_size ]] --[[ Line: 438 ]]
        --[[ Upvalues: (ref 1): v_u_34 ]]
        p97._size = p98
        v_u_34.PrimaryPart.Size = Vector3.new(p98.X, p98.Y, 0)
    end;
    v_u_33.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 442 ]]
        --[[ Upvalues: (ref 1): v_u_34 ]]
        return v_u_34.PrimaryPart.Position;
    end;
    v_u_33.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 445 ]]
        --[[ Upvalues: (ref 1): v_u_34 ]]
        return v_u_34.PrimaryPart.SurfaceGui;
    end;
    f_cons()
    return v_u_33;
end;
return v_u_23;
