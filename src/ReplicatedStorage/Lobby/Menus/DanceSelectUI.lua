-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:43 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_3 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_5 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_6 = require(game.ReplicatedStorage.Local.DebugOut)
local v_u_7 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_8 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_9 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
local v_u_10 = require(game.ReplicatedStorage.Avatar.PlayerBlobDance)
local v_u_11 = require(game.ReplicatedStorage.PlayerInfo.DanceDatabase)
local v_u_12 = require(game.ReplicatedStorage.PlayerInfo.DanceType)
local v_u_13 = require(game.ReplicatedStorage.PlayerInfo.DanceRarity)
local v_u_14 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v15 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_16 = nil
local v_u_17 = nil
v15:require_client(function() --[[ Line: 22 ]]
    --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_17 ]]
    v_u_16 = require(game.ReplicatedStorage.Lobby.Menus.PreviewCharacterUI)
    v_u_17 = require(game.ReplicatedStorage.Lobby.Menus.DanceShopUI)
end)
local v_u_26 = {
    ["ListElement"] = {},
    ["show_dance_preview_menu"] = function(_, p_u_18, p19, p_u_20) --[[ Name: show_dance_preview_menu ]] --[[ Line: 412 ]]
        --[[ Upvalues: (ref 1): v_u_16, (copy 2): v_u_11, (copy 3): v_u_12, (copy 4): v_u_1, (copy 5): v_u_13 ]]
        local v_u_21 = p_u_18._menus:push_menu(v_u_16:new(p_u_18, p_u_18._spui, p_u_18._menus))
        local v22 = v_u_21:get_character_display()
        v22:push_animation_assetid(v_u_11:singleton():get_dance_assetid_for_id(p19))
        v22:set_dance_active(true)
        v22:play_selected_animation()
        v_u_21:set_text(string.format("Dance: %s", v_u_11:singleton():get_dance_name_for_id(p19)), string.format("Type: %s\nRarity: %s", v_u_12:type_to_string(v_u_11:singleton():get_dance_type_for_id(p19)), v_u_1:enum_val_to_name(v_u_11:singleton():get_dance_rarity_for_id(p19), v_u_13)))
        local v_u_23 = p_u_20 and v_u_21:get_action_buttons():pop_back()
        if v_u_23 then
            v_u_23:set_visible(true)
            local function _() --[[ Name: update_button_text ]] --[[ Line: 431 ]]
                --[[ Upvalues: (ref 1): v_u_1, (copy 2): v_u_23 ]]
                for _, v24 in v_u_1:get_list_of_children_of_classname(v_u_23:get_part(), "TextLabel"):key_itr() do
                    v24.Text = "Buy"
                end;
            end;
            for _, v25 in v_u_1:get_list_of_children_of_classname(v_u_23:get_part(), "TextLabel"):key_itr() do
                v25.Text = "Buy"
            end;
            v_u_23:bind_data(function() --[[ Line: 438 ]]
                --[[ Upvalues: (copy 1): p_u_18, (copy 2): v_u_21, (copy 3): p_u_20 ]]
                p_u_18._menus:remove_menu(v_u_21)
                p_u_20()
            end)
        end;
    end
}
v_u_26.ListElement.new = function(_, p_u_27, p_u_28, p_u_29, p_u_30, p_u_31) --[[ Name: new ]] --[[ Line: 30 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_1, (copy 3): v_u_11, (copy 4): v_u_13, (copy 5): v_u_12, (copy 6): v_u_10 ]]
    local v32 = {}
    local v_u_33 = nil
    local v_u_34 = nil
    local v_u_35 = nil
    local v_u_36 = v_u_2:new()
    local v_u_37 = v_u_2:new()
    local v_u_38 = 1
    local v_u_39 = nil
    local v_u_40 = 1
    local function f_cons() --[[ Name: cons ]] --[[ Line: 52 ]]
        --[[ Upvalues: (ref 1): v_u_36, (ref 2): v_u_1, (copy 3): p_u_30, (ref 4): v_u_37, (ref 5): v_u_39, (copy 6): p_u_28, (ref 7): v_u_33, (ref 8): v_u_34, (ref 9): v_u_35, (copy 10): p_u_29 ]]
        v_u_36 = v_u_1:get_list_of_children_of_classname(p_u_30:get_part(), "ImageLabel")
        v_u_37 = v_u_1:get_list_of_children_of_classname(p_u_30:get_part(), "TextLabel")
        v_u_39 = p_u_28.EquipButton.SurfaceGui.Frame.Icon
        v_u_33 = p_u_28.MainSurface.SurfaceGui.Frame.IconDisplay
        v_u_34 = p_u_28.MainSurface.SurfaceGui.Frame.NameDisplay
        v_u_35 = p_u_28.MainSurface.SurfaceGui.Frame.SubDisplay
        p_u_29:set_default_sgui()
    end;
    v32.layout = function(_) --[[ Name: layout ]] --[[ Line: 63 ]]
        --[[ Upvalues: (copy 1): p_u_29 ]]
        p_u_29:layout()
    end;
    v32.set_alpha = function(p41, p42) --[[ Name: set_alpha ]] --[[ Line: 64 ]]
        --[[ Upvalues: (ref 1): v_u_40 ]]
        if v_u_40 ~= p42 then
            v_u_40 = p42
            p41:update_alphas()
        end;
    end;
    v32.update_alphas = function(_) --[[ Name: update_alphas ]] --[[ Line: 71 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_36, (ref 3): v_u_38, (ref 4): v_u_40, (ref 5): v_u_37, (copy 6): p_u_30, (copy 7): p_u_31 ]]
        v_u_1:list_set_alpha_name(v_u_36, {
            ["ImageAlpha"] = v_u_38 * v_u_40
        })
        v_u_1:list_set_alpha_name(v_u_37, {
            ["TextAlpha"] = v_u_38 * v_u_40
        })
        v_u_1:r_set_alpha(p_u_30:get_part(), v_u_40)
        v_u_1:r_set_alpha(p_u_31:get_part(), v_u_40)
    end;
    local v_u_43 = -1
    v32.set_dance_id = function(p44, p45) --[[ Name: set_dance_id ]] --[[ Line: 79 ]]
        --[[ Upvalues: (ref 1): v_u_43, (copy 2): p_u_30, (copy 3): p_u_29, (copy 4): p_u_31, (ref 5): v_u_34, (ref 6): v_u_11, (ref 7): v_u_13, (ref 8): v_u_35, (ref 9): v_u_12, (ref 10): v_u_33, (copy 11): p_u_27, (ref 12): v_u_10, (ref 13): v_u_38, (ref 14): v_u_39, (ref 15): v_u_1 ]]
        v_u_43 = p45
        p_u_30:set_visible(true)
        p_u_29:set_visible(true)
        p_u_31:set_visible(true)
        v_u_34.Text = string.format("[%d] %s", p45, v_u_11:singleton():get_dance_name_for_id(p45))
        v_u_34.TextColor3 = v_u_13:rarity_to_color(v_u_11:singleton():get_dance_rarity_for_id(p45))
        v_u_35.Text = v_u_12:type_to_string(v_u_11:singleton():get_dance_type_for_id(p45)) .. " Dance"
        v_u_33.Image = v_u_11:singleton():get_dance_icon_for_id(p45)
        if v_u_10:is_dance_equipped(p_u_27._player_blob_manager:get_player_blob(), p45) then
            v_u_38 = 1
            v_u_39.Image = v_u_1:checkmark_icon_assetid()
        else
            v_u_38 = 0.65
            v_u_39.Image = v_u_1:x_icon_assetid()
        end;
        p44:update_alphas()
    end;
    v32.get_dance_id = function(_) --[[ Name: get_dance_id ]] --[[ Line: 101 ]]
        --[[ Upvalues: (ref 1): v_u_43 ]]
        return v_u_43;
    end;
    v32.set_empty = function(_) --[[ Name: set_empty ]] --[[ Line: 103 ]]
        --[[ Upvalues: (copy 1): p_u_30, (copy 2): p_u_29, (copy 3): p_u_31 ]]
        p_u_30:set_visible(false)
        p_u_29:set_visible(false)
        p_u_31:set_visible(false)
    end;
    f_cons()
    return v32;
end;
v_u_26.new = function(_, p_u_46, p_u_47, p_u_48) --[[ Name: new ]] --[[ Line: 113 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_2, (copy 3): v_u_1, (copy 4): v_u_8, (copy 5): v_u_5, (copy 6): v_u_4, (copy 7): v_u_7, (ref 8): v_u_17, (copy 9): v_u_10, (copy 10): v_u_9, (copy 11): v_u_14, (copy 12): v_u_6, (copy 13): v_u_26, (copy 14): v_u_11, (copy 15): v_u_12 ]]
    local v_u_49 = v_u_3:new(p_u_47, p_u_48)
    local v_u_50 = nil
    local v_u_51 = 1
    local v_u_52 = 1
    local v_u_53 = nil
    local v_u_54 = nil
    local v_u_55 = v_u_2:new()
    local v_u_56 = nil
    local v_u_57 = 0
    local v_u_58 = nil
    local v_u_59 = false
    local function _() --[[ Name: get_max_page ]] --[[ Line: 130 ]]
        --[[ Upvalues: (copy 1): v_u_49, (copy 2): v_u_55 ]]
        return math.ceil(v_u_49:get_display_owned_danceid_list():count() / v_u_55:count());
    end;
    local function f_cons() --[[ Name: cons ]] --[[ Line: 135 ]]
        --[[ Upvalues: (ref 1): v_u_50, (ref 2): v_u_1, (ref 3): v_u_8, (copy 4): v_u_49, (ref 5): v_u_56, (ref 6): v_u_58, (copy 7): p_u_46, (ref 8): v_u_5, (ref 9): v_u_4, (copy 10): p_u_47, (ref 11): v_u_7, (copy 12): p_u_48, (ref 13): v_u_53, (ref 14): v_u_57, (copy 15): v_u_55, (ref 16): v_u_54, (ref 17): v_u_17, (ref 18): v_u_59, (ref 19): v_u_10 ]]
        v_u_50 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.DanceSelectUI:Clone()
        v_u_50.Name = v_u_1:gen_name(v_u_50.Name)
        v_u_50.Parent = v_u_8:get_world_ui_folder()
        v_u_49._native_size = v_u_50.PrimaryPart.Size
        v_u_49._size = v_u_49._native_size
        v_u_56 = v_u_50.MainSurface.SurfaceGui.Frame
        v_u_58 = v_u_56.ListPageDisplay
        v_u_49:add_cycle_element(p_u_46, 1, v_u_5:new(v_u_4:new(v_u_49, v_u_50.PrimaryPart, v_u_50.BackButtonSurface), p_u_47, function() --[[ Line: 149 ]]
            --[[ Upvalues: (ref 1): p_u_46, (ref 2): v_u_7, (ref 3): v_u_49, (ref 4): p_u_48 ]]
            p_u_46._sfx_manager:play_sfx(v_u_7.SFX_MENU_CLOSE)
            v_u_49:save_changes(function() --[[ Line: 151 ]]
                --[[ Upvalues: (ref 1): p_u_48, (ref 2): v_u_49 ]]
                p_u_48:remove_menu(v_u_49)
            end)
        end))
        v_u_53 = v_u_49:add_cycle_element(p_u_46, 1, v_u_5:new(v_u_4:new(v_u_49, v_u_50.PrimaryPart, v_u_50.TopArrowSurface), p_u_47, function() --[[ Line: 160 ]]
            --[[ Upvalues: (ref 1): p_u_46, (ref 2): v_u_7, (ref 3): v_u_57, (ref 4): v_u_49, (ref 5): v_u_55 ]]
            p_u_46._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
            v_u_57 = v_u_57 - 1
            if v_u_57 < 0 then
                v_u_57 = math.max(math.ceil(v_u_49:get_display_owned_danceid_list():count() / v_u_55:count()) - 1, 0)
            end;
            v_u_49:update_display_info()
        end))
        v_u_54 = v_u_49:add_cycle_element(p_u_46, 1, v_u_5:new(v_u_4:new(v_u_49, v_u_50.PrimaryPart, v_u_50.BottomArrowSurface), p_u_47, function() --[[ Line: 173 ]]
            --[[ Upvalues: (ref 1): p_u_46, (ref 2): v_u_7, (ref 3): v_u_57, (ref 4): v_u_49, (ref 5): v_u_55 ]]
            p_u_46._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
            v_u_57 = v_u_57 + 1
            if v_u_57 >= math.ceil(v_u_49:get_display_owned_danceid_list():count() / v_u_55:count()) then
                v_u_57 = 0
            end;
            v_u_49:update_display_info()
        end))
        v_u_49:add_cycle_element(p_u_46, 1, v_u_5:new(v_u_4:new(v_u_49, v_u_50.PrimaryPart, v_u_50.DanceShopButton), p_u_47, function() --[[ Line: 186 ]]
            --[[ Upvalues: (ref 1): p_u_46, (ref 2): v_u_7, (ref 3): v_u_49, (ref 4): p_u_48, (ref 5): v_u_17, (ref 6): p_u_47 ]]
            p_u_46._sfx_manager:play_sfx(v_u_7.SFX_MENU_OPEN)
            v_u_49:save_changes(function() --[[ Line: 188 ]]
                --[[ Upvalues: (ref 1): p_u_48, (ref 2): v_u_49, (ref 3): v_u_17, (ref 4): p_u_46, (ref 5): p_u_47 ]]
                p_u_48:remove_menu(v_u_49)
                p_u_48:push_menu(v_u_17:new(p_u_46, p_u_47, p_u_48))
            end)
        end))
        v_u_49:add_cycle_element(p_u_46, 1, v_u_5:new(v_u_4:new(v_u_49, v_u_50.PrimaryPart, v_u_50.ResetToDefaultButton), p_u_47, function() --[[ Line: 198 ]]
            --[[ Upvalues: (ref 1): p_u_46, (ref 2): v_u_7, (ref 3): v_u_59, (ref 4): v_u_10, (ref 5): v_u_49 ]]
            p_u_46._sfx_manager:play_sfx(v_u_7.SFX_MENU_OPEN)
            v_u_59 = true
            local v60 = p_u_46._player_blob_manager:get_player_blob()
            v_u_10:write_dance_equipped(v60, {})
            v_u_10:validate_playerblob(v60)
            v_u_49:save_changes(function() end)
        end))
        v_u_49:create_list_elements()
        v_u_49:update_display_info()
        v_u_49:reset_selected_item()
        v_u_49:transition_update_visual(0)
        v_u_49:layout()
    end;
    v_u_49.save_changes = function(p_u_61, p_u_62) --[[ Name: save_changes ]] --[[ Line: 217 ]]
        --[[ Upvalues: (ref 1): v_u_59, (copy 2): p_u_48, (ref 3): v_u_9, (copy 4): p_u_46, (copy 5): p_u_47, (ref 6): v_u_14 ]]
        if v_u_59 ~= true then
            return p_u_62();
        end;
        local v_u_63 = p_u_48:push_menu(v_u_9:new(p_u_46, p_u_47, p_u_48):set_text("Saving...", "Please wait..."):set_close_button_visible(false))
        p_u_46._evt:wait_on_event_once(v_u_14.EVT_PlayerBlob_ServerSetEquippedDancesResponse, function(p64) --[[ Line: 223 ]]
            --[[ Upvalues: (ref 1): p_u_48, (copy 2): v_u_63, (ref 3): v_u_9, (ref 4): p_u_46, (ref 5): p_u_47, (copy 6): p_u_62, (copy 7): p_u_61 ]]
            if p64 ~= true then
                p_u_48:remove_menu(v_u_63)
                p_u_48:push_menu(v_u_9:new(p_u_46, p_u_47, p_u_48):set_text("Error", "Failed"))
                return p_u_62();
            end;
            p_u_46._player_blob_manager:do_sync(function() --[[ Line: 230 ]]
                --[[ Upvalues: (ref 1): p_u_48, (ref 2): v_u_63, (ref 3): p_u_61, (ref 4): p_u_62 ]]
                p_u_48:remove_menu(v_u_63)
                p_u_61:update_display_info()
                p_u_62()
            end)
        end)
        p_u_46._evt:fire_event_to_server(v_u_14.EVT_PlayerBlob_ClientSetEquippedDances, p_u_46._player_blob_manager:get_player_blob().DanceEquipped)
        v_u_59 = false
    end;
    v_u_49.toggle_dance_id_equip = function(p65, p66) --[[ Name: toggle_dance_id_equip ]] --[[ Line: 241 ]]
        --[[ Upvalues: (ref 1): v_u_59, (copy 2): p_u_46, (ref 3): v_u_10, (ref 4): v_u_6 ]]
        v_u_59 = true
        local v67 = p_u_46._player_blob_manager:get_player_blob()
        local v68 = v_u_10:get_owned_danceid_to_equipped_dict(v67)
        if v68:contains(p66) == true then
            v_u_10:set_danceid_equipped(v67, p66, not v68:get(p66))
            v_u_10:validate_playerblob(v67)
            p65:update_display_info()
        else
            v_u_6:warnf("DanceSelectUI:toggle_dance_id_equip owned_danceid_to_equipped_dict does not contain(%s)", (tostring(p66)))
        end;
    end;
    v_u_49.create_list_elements = function(p_u_69) --[[ Name: create_list_elements ]] --[[ Line: 258 ]]
        --[[ Upvalues: (ref 1): v_u_50, (ref 2): v_u_4, (copy 3): p_u_46, (ref 4): v_u_5, (copy 5): p_u_47, (ref 6): v_u_7, (ref 7): v_u_26, (copy 8): v_u_55 ]]
        local l_DanceButtonProto_0 = v_u_50.DanceButtonProto
        l_DanceButtonProto_0.Parent = nil
        for v70 = 1, 8 do
            local l_Anchors_0 = v_u_50.Anchors["Anchor" .. tostring(v70)]
            local v71 = l_DanceButtonProto_0:Clone()
            v71:SetPrimaryPartCFrame(l_Anchors_0.CFrame)
            v71.Parent = v_u_50
            local v_u_72 = nil
            local v73 = v_u_4:new(p_u_69, v_u_50.PrimaryPart, v71.PrimaryPart)
            local v74 = v_u_26.ListElement:new(p_u_46, v71, v73, p_u_69:add_cycle_element(p_u_46, 1, v_u_5:new(v_u_4:new(v73, v71.PrimaryPart, v71.EquipButton), p_u_47, function() --[[ Line: 272 ]]
                --[[ Upvalues: (ref 1): p_u_46, (ref 2): v_u_7, (copy 3): p_u_69, (ref 4): v_u_72 ]]
                p_u_46._sfx_manager:play_sfx(v_u_7.SFX_MENU_OPEN)
                p_u_69:toggle_dance_id_equip(v_u_72:get_dance_id())
            end)):set_auto_zoffset_behaviour(true), (p_u_69:add_cycle_element(p_u_46, 1, v_u_5:new(v_u_4:new(v73, v71.PrimaryPart, v71.PreviewButton), p_u_47, function() --[[ Line: 280 ]]
                --[[ Upvalues: (ref 1): p_u_46, (ref 2): v_u_7, (ref 3): v_u_26, (ref 4): v_u_72 ]]
                p_u_46._sfx_manager:play_sfx(v_u_7.SFX_MENU_OPEN)
                v_u_26:show_dance_preview_menu(p_u_46, v_u_72:get_dance_id())
            end)):set_auto_zoffset_behaviour(true)))
            v_u_55:push_back(v74)
        end;
    end;
    v_u_49.get_display_owned_danceid_list = function(_) --[[ Name: get_display_owned_danceid_list ]] --[[ Line: 297 ]]
        --[[ Upvalues: (copy 1): p_u_46, (ref 2): v_u_10, (ref 3): v_u_2, (ref 4): v_u_11, (ref 5): v_u_12 ]]
        local v75 = v_u_10:get_owned_danceid_to_equipped_dict((p_u_46._player_blob_manager:get_player_blob()))
        local v76 = v_u_2:new()
        for v77, _ in v_u_11:singleton():key_itr() do
            if v75:contains(v77) then
                v76:push_back(v77)
            end;
        end;
        return v76:remove_if(function(p78) --[[ Line: 306 ]]
            --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_12 ]]
            local v79 = v_u_11:singleton():get_dance_type_for_id(p78)
            return v79 ~= v_u_12.OnMiss and v79 ~= v_u_12.Standard and v79 ~= v_u_12.Combo;
        end);
    end;
    v_u_49.update_display_info = function(p80) --[[ Name: update_display_info ]] --[[ Line: 312 ]]
        --[[ Upvalues: (copy 1): p_u_46, (ref 2): v_u_10, (ref 3): v_u_11, (ref 4): v_u_12, (ref 5): v_u_56, (copy 6): v_u_55, (ref 7): v_u_57, (ref 8): v_u_53, (ref 9): v_u_54, (ref 10): v_u_58, (copy 11): v_u_49 ]]
        local v81 = 0
        local v82 = 0
        local v83 = 0
        for v84, v85 in v_u_10:get_owned_danceid_to_equipped_dict((p_u_46._player_blob_manager:get_player_blob())):key_itr() do
            if v85 == true then
                local v86 = v_u_11:singleton():get_dance_type_for_id(v84)
                if v86 == v_u_12.OnMiss then
                    v81 = v81 + 1
                elseif v86 == v_u_12.Standard then
                    v82 = v82 + 1
                elseif v86 == v_u_12.Combo then
                    v83 = v83 + 1
                end;
            end;
        end;
        v_u_56.OnMissDanceDisplay.Text = string.format("%d Active Dance(s)", v81)
        v_u_56.StandardDanceDisplay.Text = string.format("%d Active Dance(s)", v82)
        v_u_56.ComboDanceDisplay.Text = string.format("%d Active Dance(s)", v83)
        local v87 = p80:get_display_owned_danceid_list()
        for v88 = 1, v_u_55:count() do
            local v89 = v_u_55:get(v88)
            local v90 = v_u_57 * v_u_55:count() + v88
            if v90 <= v87:count() then
                v89:set_dance_id(v87:get(v90))
            else
                v89:set_empty()
            end;
        end;
        v_u_53:set_visible(true)
        v_u_54:set_visible(true)
        v_u_58.Text = string.format("%d/%d", v_u_57 + 1, (math.ceil(v_u_49:get_display_owned_danceid_list():count() / v_u_55:count())))
    end;
    v_u_49.behaviour_update = function(p91, p92, p93) --[[ Name: behaviour_update ]] --[[ Line: 354 ]]
        p91:behaviour_update_base(p92, p93)
    end;
    v_u_49.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 358 ]]
        --[[ Upvalues: (ref 1): v_u_50 ]]
        v_u_50:Destroy()
    end;
    v_u_49.layout = function(p94) --[[ Name: layout ]] --[[ Line: 362 ]]
        --[[ Upvalues: (copy 1): p_u_47, (ref 2): v_u_52, (ref 3): v_u_50, (copy 4): v_u_55 ]]
        p94:opt_rescale_to_max_nxy(p_u_47, 0.85, 0.85, v_u_52)
        local v95, v96 = p94:opt_update_cframe_params(p_u_47, {
            ["PositionNXY"] = Vector2.new(0.5, 0.5),
            ["OffsetXYZ"] = p94:anchored_offset(0.5, 0.5),
            ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
        })
        if v95 == true then
            v_u_50:SetPrimaryPartCFrame(v96)
        end;
        for v97 = 1, v_u_55:count() do
            v_u_55:get(v97):layout()
        end;
    end;
    v_u_49.set_alpha = function(_, p98) --[[ Name: set_alpha ]] --[[ Line: 378 ]]
        --[[ Upvalues: (ref 1): v_u_51, (copy 2): v_u_55, (ref 3): v_u_1, (ref 4): v_u_50 ]]
        if v_u_51 ~= p98 then
            v_u_51 = p98
            for v99 = 1, v_u_55:count() do
                v_u_55:get(v99):set_alpha(p98)
            end;
            v_u_1:r_set_alpha(v_u_50, v_u_51)
        end;
    end;
    v_u_49.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 387 ]]
        --[[ Upvalues: (ref 1): v_u_51 ]]
        return v_u_51;
    end;
    v_u_49.set_scale = function(_, p100) --[[ Name: set_scale ]] --[[ Line: 388 ]]
        --[[ Upvalues: (ref 1): v_u_52 ]]
        v_u_52 = p100
    end;
    v_u_49.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 389 ]]
        --[[ Upvalues: (ref 1): v_u_52 ]]
        return v_u_52;
    end;
    v_u_49.get_native_size = function(p101) --[[ Name: get_native_size ]] --[[ Line: 391 ]]
        return p101._native_size;
    end;
    v_u_49.get_size = function(p102) --[[ Name: get_size ]] --[[ Line: 394 ]]
        return p102._size;
    end;
    v_u_49.set_size = function(p103, p104) --[[ Name: set_size ]] --[[ Line: 397 ]]
        --[[ Upvalues: (ref 1): v_u_50 ]]
        p103._size = p104
        v_u_50.PrimaryPart.Size = Vector3.new(p104.X, p104.Y, 0)
    end;
    v_u_49.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 401 ]]
        --[[ Upvalues: (ref 1): v_u_50 ]]
        return v_u_50.PrimaryPart.Position;
    end;
    v_u_49.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 404 ]]
        --[[ Upvalues: (ref 1): v_u_50 ]]
        return v_u_50.PrimaryPart.SurfaceGui;
    end;
    f_cons()
    return v_u_49;
end;
return v_u_26;
