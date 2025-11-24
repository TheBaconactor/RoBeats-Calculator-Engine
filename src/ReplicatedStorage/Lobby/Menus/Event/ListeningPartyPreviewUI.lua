-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:49 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_3 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_5 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_6 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_7 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_8 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
require(game.ReplicatedStorage.Shared.ListAdapter)
local v_u_9 = require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.Lobby.UI.SongDisplayElement)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_10 = require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfo)
require(game.ReplicatedStorage.Shared.PlayerSettings)
local v_u_11 = require(game.ReplicatedStorage.Lobby.UI.ScrollingElementDisplay)
local v_u_12 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
local v_u_13 = require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfoData.MiscEventInfo)
local v14 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_15 = nil
local v_u_16 = nil
local v_u_17 = nil
local v_u_18 = nil
v14:require_client(function() --[[ Line: 29 ]]
    --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_16, (ref 3): v_u_17, (ref 4): v_u_18 ]]
    v_u_15 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
    v_u_16 = require(game.ReplicatedStorage.Lobby.Menus.MatchMakingV3UI)
    v_u_17 = require(game.ReplicatedStorage.Lobby.UI.MatchMakingV3GameStageSelectSection)
    v_u_18 = require(game.ReplicatedStorage.Lobby.Menus.RewardDescriptionInfoAcquiredUI)
end)
local v19 = {}
local v_u_20 = v_u_2:new({
    {
        ["Name"] = "01 - Yesterwynde",
        ["AssetId"] = "rbxassetid://129020651358838"
    },
    {
        ["Name"] = "03 - The Antikythera Mechanism",
        ["AssetId"] = "rbxassetid://97051169232021"
    },
    {
        ["Name"] = "05 - Perfume Of The Timeless",
        ["AssetId"] = "rbxassetid://97244069745059"
    },
    {
        ["Name"] = "06 - Sway",
        ["AssetId"] = "rbxassetid://89605311725088"
    },
    {
        ["Name"] = "07 - The Children Of \'Ata",
        ["AssetId"] = "rbxassetid://111546997382543"
    },
    {
        ["Name"] = "08 - Something Whispered Follow Me",
        ["AssetId"] = "rbxassetid://140570608862921"
    },
    {
        ["Name"] = "09 - Spider Silk",
        ["AssetId"] = "rbxassetid://76699759971238"
    },
    {
        ["Name"] = "10 - Hiraeth",
        ["AssetId"] = "rbxassetid://97649758140702"
    },
    {
        ["Name"] = "11 - The Weave",
        ["AssetId"] = "rbxassetid://134631203873123"
    },
    {
        ["Name"] = "12 - Lanternlight",
        ["AssetId"] = "rbxassetid://89926528991685"
    }
})
local v_u_21 = v_u_1:rand_rangei(1, v_u_20:count() + 1)
v19.new = function(_, p_u_22, p_u_23, p_u_24) --[[ Name: new ]] --[[ Line: 147 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_5, (copy 3): v_u_4, (copy 4): v_u_6, (copy 5): v_u_2, (copy 6): v_u_13, (ref 7): v_u_15, (copy 8): v_u_12, (ref 9): v_u_18, (copy 10): v_u_10, (copy 11): v_u_7, (copy 12): v_u_11, (copy 13): v_u_20, (ref 14): v_u_21, (copy 15): v_u_9, (copy 16): v_u_1, (copy 17): v_u_8 ]]
    local v_u_25 = v_u_3:new(p_u_23, p_u_24)
    local v_u_26 = nil
    local v_u_27 = nil
    local v_u_28 = nil
    local v_u_29 = nil
    local v_u_30 = true
    local function f_cons() --[[ Name: cons ]] --[[ Line: 157 ]]
        --[[ Upvalues: (ref 1): v_u_26, (copy 2): v_u_25, (ref 3): v_u_28, (copy 4): p_u_22, (ref 5): v_u_5, (ref 6): v_u_4, (copy 7): p_u_23, (ref 8): v_u_6, (copy 9): p_u_24, (ref 10): v_u_2, (ref 11): v_u_13, (ref 12): v_u_15, (ref 13): v_u_12, (ref 14): v_u_18, (ref 15): v_u_27, (ref 16): v_u_10, (ref 17): v_u_7, (ref 18): v_u_29, (ref 19): v_u_11, (ref 20): v_u_20, (ref 21): v_u_21, (ref 22): v_u_9, (ref 23): v_u_30 ]]
        v_u_26 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.Event.ListeningPartyPreviewUI:Clone()
        v_u_25:set_showing(true)
        v_u_28 = p_u_22._bgm_manager:begin_preview_songkey()
        v_u_25._native_size = v_u_26.PrimaryPart.Size
        v_u_25._size = v_u_25._native_size
        v_u_25:add_cycle_element(p_u_22, 1, v_u_5:new(v_u_4:new(v_u_25, v_u_26.PrimaryPart, v_u_26.BackButtonSurface), p_u_23, function() --[[ Line: 169 ]]
            --[[ Upvalues: (ref 1): p_u_22, (ref 2): v_u_6, (ref 3): p_u_24, (ref 4): v_u_25 ]]
            p_u_22._sfx_manager:play_sfx(v_u_6.SFX_MENU_CLOSE)
            p_u_24:remove_menu(v_u_25)
        end))
        local l_LoadedSection_0 = v_u_26.MainSurface.SurfaceGui.Frame.LoadedSection
        l_LoadedSection_0.Banner.Image = "rbxassetid://83230969538195"
        local v31 = v_u_2:new({ l_LoadedSection_0.RewardSection.Reward1 })
        local v32 = v_u_13:get_listening_party_reward_list()
        for _, v33 in v31:key_itr() do
            v33.Visible = false
        end;
        for _, v34 in v32:key_itr() do
            if v31:count() == 0 then
                break;
            end;
            local v35 = v31:pop_front()
            v35.Visible = true
            v35.Text.Text = v34:get_name()
            v35.Icon.Image = v34:get_image()
        end;
        local function f_claim_button_handle_response(p36, p37) --[[ Name: claim_button_handle_response ]] --[[ Line: 195 ]]
            --[[ Upvalues: (ref 1): p_u_22, (ref 2): v_u_6, (ref 3): v_u_15, (ref 4): p_u_23, (ref 5): p_u_24, (ref 6): v_u_12, (ref 7): v_u_18 ]]
            p_u_22._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
            local v_u_38 = p_u_22._menus:push_menu(v_u_15:new(p_u_22, p_u_23, p_u_24):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
            p_u_22._evt:wait_on_event_once(p37, function(p39, p40, p_u_41) --[[ Line: 202 ]]
                --[[ Upvalues: (ref 1): p_u_22, (copy 2): v_u_38, (ref 3): p_u_24, (ref 4): v_u_15, (ref 5): p_u_23, (ref 6): v_u_6, (ref 7): v_u_12, (ref 8): v_u_18 ]]
                if p39 == true then
                    p_u_22._player_blob_manager:do_sync(function(_) --[[ Line: 209 ]]
                        --[[ Upvalues: (ref 1): p_u_22, (ref 2): v_u_38, (ref 3): v_u_12, (copy 4): p_u_41, (ref 5): v_u_18, (ref 6): p_u_23, (ref 7): p_u_24, (ref 8): v_u_6 ]]
                        p_u_22._menus:remove_menu(v_u_38)
                        p_u_22._menus:push_menu(v_u_18:new(p_u_22, p_u_23, p_u_24, (v_u_12.RewardInfo:table_to_list(p_u_41))):set_header_text("Rewards"))
                        p_u_22._sfx_manager:play_sfx(v_u_6.SFX_ACQUIRE)
                    end)
                else
                    p_u_22._menus:remove_menu(v_u_38)
                    p_u_24:push_menu(v_u_15:new(p_u_22, p_u_23, p_u_24):set_text("Failed", p40))
                    p_u_22._sfx_manager:play_sfx(v_u_6.SFX_FAIL)
                end;
            end)
            p_u_22._evt:fire_event_to_server(p36)
        end;
        v_u_27 = v_u_25:add_cycle_element(p_u_22, 1, v_u_5:new(v_u_4:new(v_u_25, v_u_26.PrimaryPart, v_u_26.ClaimButton), p_u_23, function() --[[ Line: 225 ]]
            --[[ Upvalues: (ref 1): p_u_22, (ref 2): v_u_10, (copy 3): f_claim_button_handle_response, (ref 4): v_u_7 ]]
            v_u_10:confirm_if_playerblob_cannot_add_any_more_gear(p_u_22, p_u_22._player_blob_manager:get_player_blob(), function() --[[ Line: 227 ]]
                --[[ Upvalues: (ref 1): f_claim_button_handle_response, (ref 2): v_u_7 ]]
                f_claim_button_handle_response(v_u_7.EVT_SpecialEvent_Misc_ClientRequest1, v_u_7.EVT_SpecialEvent_Misc_ServerResponse1)
            end)
        end))
        v_u_5:button_add_enabled_anim(v_u_27, function() --[[ Line: 235 ]]
            --[[ Upvalues: (ref 1): v_u_25 ]]
            return v_u_25:get_alpha();
        end)
        v_u_25:update_claim_button_status()
        v_u_29 = v_u_11:new(l_LoadedSection_0.ScrollingFrame.ScrollText1, l_LoadedSection_0.ScrollingFrame.ScrollText2)
        local function _() --[[ Name: update_scrolling_display ]] --[[ Line: 239 ]]
            --[[ Upvalues: (ref 1): v_u_20, (ref 2): v_u_21, (ref 3): v_u_29, (ref 4): p_u_22, (ref 5): v_u_9 ]]
            local v42 = v_u_20:get(v_u_21)
            v_u_29:set_text("Now Playing: " .. v42.Name .. " - Album \'Yesterwynde\' by Nightwish available now! ")
            p_u_22._bgm_manager:preview_songkey(v_u_9:invalid_songkey(), v42.AssetId, false)
        end;
        local v43 = v_u_20:get(v_u_21)
        v_u_29:set_text("Now Playing: " .. v43.Name .. " - Album \'Yesterwynde\' by Nightwish available now! ")
        p_u_22._bgm_manager:preview_songkey(v_u_9:invalid_songkey(), v43.AssetId, false)
        v_u_25:add_cycle_element(p_u_22, 1, v_u_5:new(v_u_4:new(v_u_25, v_u_26.PrimaryPart, v_u_26.ScrollButtonLeft), p_u_23, function() --[[ Line: 249 ]]
            --[[ Upvalues: (ref 1): p_u_22, (ref 2): v_u_6, (ref 3): v_u_21, (ref 4): v_u_20, (ref 5): v_u_29, (ref 6): v_u_9 ]]
            p_u_22._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
            v_u_21 = v_u_21 - 1
            if v_u_21 < 1 then
                v_u_21 = v_u_20:count()
            end;
            local v44 = v_u_20:get(v_u_21)
            v_u_29:set_text("Now Playing: " .. v44.Name .. " - Album \'Yesterwynde\' by Nightwish available now! ")
            p_u_22._bgm_manager:preview_songkey(v_u_9:invalid_songkey(), v44.AssetId, false)
        end))
        v_u_25:add_cycle_element(p_u_22, 1, v_u_5:new(v_u_4:new(v_u_25, v_u_26.PrimaryPart, v_u_26.ScrollButtonRight), p_u_23, function() --[[ Line: 262 ]]
            --[[ Upvalues: (ref 1): p_u_22, (ref 2): v_u_6, (ref 3): v_u_21, (ref 4): v_u_20, (ref 5): v_u_29, (ref 6): v_u_9 ]]
            p_u_22._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
            v_u_21 = v_u_21 + 1
            if v_u_21 > v_u_20:count() then
                v_u_21 = 1
            end;
            local v45 = v_u_20:get(v_u_21)
            v_u_29:set_text("Now Playing: " .. v45.Name .. " - Album \'Yesterwynde\' by Nightwish available now! ")
            p_u_22._bgm_manager:preview_songkey(v_u_9:invalid_songkey(), v45.AssetId, false)
        end))
        v_u_25:add_cycle_element(p_u_22, 1, v_u_5:new(v_u_4:new(v_u_25, v_u_26.PrimaryPart, v_u_26.PreviewButton), p_u_23, function() --[[ Line: 275 ]]
            --[[ Upvalues: (ref 1): p_u_22, (ref 2): v_u_6, (ref 3): v_u_20, (ref 4): v_u_21, (ref 5): v_u_9, (ref 6): v_u_30, (ref 7): v_u_25 ]]
            p_u_22._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
            p_u_22._bgm_manager:preview_songkey(v_u_9:invalid_songkey(), v_u_20:get(v_u_21).AssetId, true)
            v_u_30 = false
            p_u_22._menus:remove_menu(v_u_25)
        end))
        v_u_25:transition_update_visual(0)
        v_u_25:layout()
    end;
    v_u_25.update_claim_button_status = function(_) --[[ Name: update_claim_button_status ]] --[[ Line: 289 ]]
        --[[ Upvalues: (copy 1): p_u_22, (ref 2): v_u_13, (ref 3): v_u_27 ]]
        if v_u_13:playerblob_test_owns_listening_party_reward(p_u_22._player_blob_manager:get_player_blob(), p_u_22._player_blob_manager:get_cached_collection_info()) == true then
            v_u_27:set_enabled(false)
        else
            v_u_27:set_enabled(true)
        end;
    end;
    v_u_25.on_refocus = function(p46) --[[ Name: on_refocus ]] --[[ Line: 298 ]]
        p46:update_claim_button_status()
    end;
    v_u_25.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 302 ]]
        --[[ Upvalues: (ref 1): v_u_26, (ref 2): v_u_30, (copy 3): p_u_22, (ref 4): v_u_28 ]]
        v_u_26:Destroy()
        if v_u_30 then
            p_u_22._bgm_manager:stop_song_preview(v_u_28)
        end;
    end;
    v_u_25.visual_update = function(p47, p48, p49) --[[ Name: visual_update ]] --[[ Line: 310 ]]
        --[[ Upvalues: (copy 1): p_u_22 ]]
        if p_u_22:transition_local_camera_cframe_finished() ~= false then
            p47:visual_update_base(p48, p49)
        end;
    end;
    v_u_25.behaviour_update = function(p50, p51, _) --[[ Name: behaviour_update ]] --[[ Line: 318 ]]
        --[[ Upvalues: (copy 1): p_u_22, (ref 2): v_u_29 ]]
        p50:behaviour_update_base(p51, p_u_22)
        v_u_29:update(p51)
    end;
    local v_u_52 = 1
    local v_u_53 = 1
    v_u_25.layout = function(p54) --[[ Name: layout ]] --[[ Line: 325 ]]
        --[[ Upvalues: (copy 1): p_u_23, (ref 2): v_u_53, (ref 3): v_u_26 ]]
        p54:opt_rescale_to_max_nxy(p_u_23, 0.8, 0.8, v_u_53)
        local v55, v56 = p54:opt_update_cframe_params(p_u_23, {
            ["PositionNXY"] = Vector2.new(0.5, 0.5),
            ["OffsetXYZ"] = p54:anchored_offset(0.5, 0.5),
            ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
        })
        if v55 == true then
            v_u_26:SetPrimaryPartCFrame(v56)
        end;
    end;
    v_u_25.set_alpha = function(_, p57) --[[ Name: set_alpha ]] --[[ Line: 337 ]]
        --[[ Upvalues: (ref 1): v_u_52, (ref 2): v_u_1, (ref 3): v_u_26 ]]
        if v_u_52 ~= p57 then
            v_u_52 = p57
            v_u_1:r_set_alpha(v_u_26, v_u_52)
        end;
    end;
    v_u_25.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 343 ]]
        --[[ Upvalues: (ref 1): v_u_52 ]]
        return v_u_52;
    end;
    v_u_25.set_scale = function(_, p58) --[[ Name: set_scale ]] --[[ Line: 344 ]]
        --[[ Upvalues: (ref 1): v_u_53 ]]
        v_u_53 = p58
    end;
    v_u_25.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 345 ]]
        --[[ Upvalues: (ref 1): v_u_53 ]]
        return v_u_53;
    end;
    v_u_25.get_native_size = function(p59) --[[ Name: get_native_size ]] --[[ Line: 347 ]]
        return p59._native_size;
    end;
    v_u_25.get_size = function(p60) --[[ Name: get_size ]] --[[ Line: 350 ]]
        return p60._size;
    end;
    v_u_25.set_size = function(p61, p62) --[[ Name: set_size ]] --[[ Line: 353 ]]
        --[[ Upvalues: (ref 1): v_u_26 ]]
        p61._size = p62
        v_u_26.PrimaryPart.Size = Vector3.new(p62.X, p62.Y, 0)
    end;
    v_u_25.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 357 ]]
        --[[ Upvalues: (ref 1): v_u_26 ]]
        return v_u_26.PrimaryPart.Position;
    end;
    v_u_25.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 360 ]]
        --[[ Upvalues: (ref 1): v_u_26 ]]
        return v_u_26.PrimaryPart.SurfaceGui;
    end;
    v_u_25.set_showing = function(_, p63) --[[ Name: set_showing ]] --[[ Line: 363 ]]
        --[[ Upvalues: (ref 1): v_u_26, (ref 2): v_u_8 ]]
        if p63 then
            v_u_26.Parent = v_u_8:get_world_ui_folder()
        else
            v_u_26.Parent = nil
        end;
    end;
    f_cons()
    return v_u_25;
end;
return v19;
