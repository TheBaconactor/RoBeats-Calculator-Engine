-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:42 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_4 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_6 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_7 = require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_8 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_9 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_10 = require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
local v_u_11 = require(game.ReplicatedStorage.Lobby.UI.GearEquipV2UI.GearSort)
local v_u_12 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentDatabase)
local v13 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_14 = nil
local v_u_15 = nil
v13:require_client(function() --[[ Line: 20 ]]
    --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_15 ]]
    v_u_14 = require(game.ReplicatedStorage.Lobby.Menus.UpgradeEditUI)
    v_u_15 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
end)
local v_u_16 = require(game.ReplicatedStorage.Lobby.UI.GearEquipV2UI.GearEquipV2GearStatDisplay)
local v_u_36 = {
    ["new"] = function(_, _, p_u_17, p_u_18, p_u_19) --[[ Name: new ]] --[[ Line: 29 ]]
        --[[ Upvalues: (copy 1): v_u_2 ]]
        local v20 = {}
        local v_u_21 = true
        local v_u_22 = -1
        v20.get_owned_id = function(_) --[[ Name: get_owned_id ]] --[[ Line: 34 ]]
            --[[ Upvalues: (ref 1): v_u_22 ]]
            return v_u_22;
        end;
        local v_u_23 = v_u_2:new()
        v20.get_uichild = function(_) --[[ Name: get_uichild ]] --[[ Line: 37 ]]
            --[[ Upvalues: (copy 1): p_u_17 ]]
            return p_u_17;
        end;
        v20.set_owned_obj = function(p24, p25, p26) --[[ Name: set_owned_obj ]] --[[ Line: 39 ]]
            --[[ Upvalues: (ref 1): v_u_22, (copy 2): p_u_18, (copy 3): p_u_19 ]]
            v_u_22 = p26
            p_u_18:set_owned_obj(p25, p26)
            if p_u_19 == nil then
                p24:set_buttons_visible(true)
            else
                p24:set_buttons_visible(p_u_19(p25, p26))
            end;
        end;
        v20.set_empty_slot = function(p27, p28) --[[ Name: set_empty_slot ]] --[[ Line: 49 ]]
            --[[ Upvalues: (copy 1): p_u_18 ]]
            p_u_18:set_empty_slot(p28)
            p27:set_buttons_visible(false)
        end;
        v20.set_hidden = function(p29) --[[ Name: set_hidden ]] --[[ Line: 54 ]]
            --[[ Upvalues: (copy 1): p_u_18 ]]
            p_u_18:set_hidden()
            p29:set_buttons_visible(false)
        end;
        v20.add_child_uibutton = function(p30, p31) --[[ Name: add_child_uibutton ]] --[[ Line: 59 ]]
            --[[ Upvalues: (copy 1): v_u_23, (ref 2): v_u_21 ]]
            v_u_23:push_back(p31)
            p30:set_buttons_visible(v_u_21)
        end;
        v20.layout = function(_) --[[ Name: layout ]] --[[ Line: 64 ]]
            --[[ Upvalues: (copy 1): p_u_17, (copy 2): v_u_23 ]]
            p_u_17:layout()
            for v32 = 1, v_u_23:count() do
                v_u_23:get(v32):layout()
            end;
        end;
        v20.set_buttons_visible = function(_, p33) --[[ Name: set_buttons_visible ]] --[[ Line: 71 ]]
            --[[ Upvalues: (ref 1): v_u_21, (copy 2): v_u_23 ]]
            v_u_21 = p33
            for v34 = 1, v_u_23:count() do
                v_u_23:get(v34):set_visible(p33)
            end;
        end;
        v20.visual_update = function(_, p35, _) --[[ Name: visual_update ]] --[[ Line: 78 ]]
            --[[ Upvalues: (copy 1): p_u_18 ]]
            p_u_18:visual_update(p35)
        end;
        return v20;
    end
}
local v_u_65 = {
    ["initialize_ui_sections"] = function(_, p37, p_u_38) --[[ Name: initialize_ui_sections ]] --[[ Line: 345 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_1 ]]
        return (function(p_u_39) --[[ Line: 346 ]]
            --[[ Upvalues: (ref 1): v_u_3, (copy 2): p_u_38, (ref 3): v_u_1 ]]
            local v40 = v_u_3:SPUIObjectBase()
            v40._native_size = p_u_39.PrimaryPart.Size
            v40._size = v40._native_size
            local v_u_41 = 1
            local v_u_42 = 1
            v40.layout = function(p43) --[[ Name: layout ]] --[[ Line: 353 ]]
                --[[ Upvalues: (ref 1): p_u_38, (ref 2): v_u_42, (copy 3): p_u_39 ]]
                p43:opt_rescale_to_max_nxy(p_u_38, 0.3, 0.7, v_u_42)
                local v44, v45 = p43:opt_update_cframe_params(p_u_38, {
                    ["PositionNXY"] = Vector2.new(0.485, 0.5),
                    ["OffsetXYZ"] = p43:anchored_offset(1, 0.5) + Vector3.new(p_u_38:get_size_from_nxy(0, 0).X),
                    ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
                })
                if v44 == true then
                    p_u_39:SetPrimaryPartCFrame(v45)
                end;
            end;
            v40.set_alpha = function(_, p46) --[[ Name: set_alpha ]] --[[ Line: 365 ]]
                --[[ Upvalues: (ref 1): v_u_41, (ref 2): v_u_1, (copy 3): p_u_39 ]]
                if v_u_41 ~= p46 then
                    v_u_41 = p46
                    v_u_1:r_set_alpha(p_u_39, v_u_41)
                end;
            end;
            v40.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 371 ]]
                --[[ Upvalues: (ref 1): v_u_41 ]]
                return v_u_41;
            end;
            v40.set_scale = function(_, p47) --[[ Name: set_scale ]] --[[ Line: 372 ]]
                --[[ Upvalues: (ref 1): v_u_42 ]]
                v_u_42 = p47
            end;
            v40.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 373 ]]
                --[[ Upvalues: (ref 1): v_u_42 ]]
                return v_u_42;
            end;
            v40.get_native_size = function(p48) --[[ Name: get_native_size ]] --[[ Line: 374 ]]
                return p48._native_size;
            end;
            v40.get_size = function(p49) --[[ Name: get_size ]] --[[ Line: 375 ]]
                return p49._size;
            end;
            v40.set_size = function(p50, p51) --[[ Name: set_size ]] --[[ Line: 376 ]]
                --[[ Upvalues: (copy 1): p_u_39 ]]
                p50._size = p51
                p_u_39.PrimaryPart.Size = Vector3.new(p51.X, p51.Y, 0)
            end;
            v40.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 380 ]]
                --[[ Upvalues: (copy 1): p_u_39 ]]
                return p_u_39.PrimaryPart.Position;
            end;
            v40.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 381 ]]
                --[[ Upvalues: (copy 1): p_u_39 ]]
                return p_u_39.PrimaryPart.SurfaceGui;
            end;
            return v40;
        end)(p37.Equipped), (function(p_u_52) --[[ Line: 385 ]]
            --[[ Upvalues: (ref 1): v_u_3, (copy 2): p_u_38, (ref 3): v_u_1 ]]
            local v53 = v_u_3:SPUIObjectBase()
            v53._native_size = p_u_52.PrimaryPart.Size
            v53._size = v53._native_size
            local v_u_54 = 1
            local v_u_55 = 1
            v53.layout = function(p56) --[[ Name: layout ]] --[[ Line: 392 ]]
                --[[ Upvalues: (ref 1): p_u_38, (ref 2): v_u_55, (copy 3): p_u_52 ]]
                p56:opt_rescale_to_max_nxy(p_u_38, 0.35, 0.8, v_u_55)
                local v57, v58 = p56:opt_update_cframe_params(p_u_38, {
                    ["PositionNXY"] = Vector2.new(0.515, 0.5),
                    ["OffsetXYZ"] = p56:anchored_offset(0, 0.5) + Vector3.new(p_u_38:get_size_from_nxy(0, 0).X),
                    ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
                })
                if v57 == true then
                    p_u_52:SetPrimaryPartCFrame(v58)
                end;
            end;
            v53.set_alpha = function(_, p59) --[[ Name: set_alpha ]] --[[ Line: 404 ]]
                --[[ Upvalues: (ref 1): v_u_54, (ref 2): v_u_1, (copy 3): p_u_52 ]]
                if v_u_54 ~= p59 then
                    v_u_54 = p59
                    v_u_1:r_set_alpha(p_u_52, v_u_54)
                end;
            end;
            v53.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 410 ]]
                --[[ Upvalues: (ref 1): v_u_54 ]]
                return v_u_54;
            end;
            v53.set_scale = function(_, p60) --[[ Name: set_scale ]] --[[ Line: 411 ]]
                --[[ Upvalues: (ref 1): v_u_55 ]]
                v_u_55 = p60
            end;
            v53.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 412 ]]
                --[[ Upvalues: (ref 1): v_u_55 ]]
                return v_u_55;
            end;
            v53.get_native_size = function(p61) --[[ Name: get_native_size ]] --[[ Line: 413 ]]
                return p61._native_size;
            end;
            v53.get_size = function(p62) --[[ Name: get_size ]] --[[ Line: 414 ]]
                return p62._size;
            end;
            v53.set_size = function(p63, p64) --[[ Name: set_size ]] --[[ Line: 415 ]]
                --[[ Upvalues: (copy 1): p_u_52 ]]
                p63._size = p64
                p_u_52.PrimaryPart.Size = Vector3.new(p64.X, p64.Y, 0)
            end;
            v53.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 419 ]]
                --[[ Upvalues: (copy 1): p_u_52 ]]
                return p_u_52.PrimaryPart.Position;
            end;
            v53.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 420 ]]
                --[[ Upvalues: (copy 1): p_u_52 ]]
                return p_u_52.PrimaryPart.SurfaceGui;
            end;
            return v53;
        end)(p37.Owned);
    end
}
v_u_65.new = function(_, p_u_66, p_u_67, p_u_68, p_u_69, p_u_70, p_u_71) --[[ Name: new ]] --[[ Line: 86 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_2, (copy 3): v_u_1, (copy 4): v_u_8, (copy 5): v_u_65, (copy 6): v_u_6, (copy 7): v_u_5, (copy 8): v_u_7, (copy 9): v_u_10, (copy 10): v_u_11, (copy 11): v_u_36, (copy 12): v_u_16, (copy 13): v_u_9 ]]
    local v72 = v_u_4:new(p_u_67, p_u_68)
    local v_u_73 = nil
    local v_u_74 = 1
    local v_u_75 = 1
    local v_u_76 = nil
    local v_u_77 = nil
    local v_u_78 = v_u_2:new()
    v72.cons = function(p_u_79) --[[ Name: cons ]] --[[ Line: 106 ]]
        --[[ Upvalues: (ref 1): v_u_73, (ref 2): v_u_1, (ref 3): v_u_8, (copy 4): p_u_67, (ref 5): v_u_76, (ref 6): v_u_77, (ref 7): v_u_65, (copy 8): p_u_66, (ref 9): v_u_6, (ref 10): v_u_5, (ref 11): v_u_7 ]]
        v_u_73 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.GearSelectUI:Clone()
        v_u_73.Name = v_u_1:gen_name(v_u_73.Name)
        v_u_73.Parent = v_u_8:get_world_ui_folder()
        p_u_79._native_size = p_u_67:get_size_from_nxy(1, 1)
        p_u_79._size = p_u_79._native_size
        v_u_73.PrimaryPart.Parent = nil
        local v80, v81 = v_u_65:initialize_ui_sections(v_u_73, p_u_67)
        v_u_76 = v80
        v_u_77 = v81
        p_u_79:initialize_equipped_section_gear_displays(v_u_73.Equipped.Anchors, v_u_73.Equipped.GearElementProto, v_u_73.Equipped, v_u_76)
        p_u_79:initialize_owned_section_gear_displays(v_u_73.Owned.Anchors, v_u_73.Owned.GearElementProto, v_u_73.Owned, v_u_77)
        p_u_79:add_cycle_element(p_u_66, 1, v_u_6:new(v_u_5:new(v_u_77, v_u_73.Owned.PrimaryPart, v_u_73.Owned.BackButtonSurface), p_u_67, function() --[[ Line: 123 ]]
            --[[ Upvalues: (ref 1): p_u_66, (ref 2): v_u_7, (copy 3): p_u_79 ]]
            p_u_66._sfx_manager:play_sfx(v_u_7.SFX_MENU_CLOSE)
            p_u_79:back_action()
        end))
        p_u_79:transition_update_visual(0)
        p_u_79:layout()
    end;
    v72.back_action = function(p82) --[[ Name: back_action ]] --[[ Line: 133 ]]
        --[[ Upvalues: (copy 1): p_u_68, (copy 2): p_u_71 ]]
        p_u_68:remove_menu(p82)
        if p_u_71 ~= nil then
            p_u_71()
        end;
    end;
    v72.owned_id_selected = function(p83, p84, p85) --[[ Name: owned_id_selected ]] --[[ Line: 140 ]]
        --[[ Upvalues: (copy 1): p_u_66, (ref 2): v_u_7, (ref 3): v_u_10, (copy 4): p_u_68, (copy 5): p_u_69 ]]
        p_u_66._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
        local _, v86 = v_u_10:playerblob_ownedid_to_equipmentid(p84, p85)
        if v86 == nil then
            p83:back_action()
        else
            p_u_68:remove_menu(p83)
            p_u_69(p84, p85)
        end;
    end;
    v72.initialize_owned_section_gear_displays = function(p_u_87, _, p88, p89, p90) --[[ Name: initialize_owned_section_gear_displays ]] --[[ Line: 151 ]]
        --[[ Upvalues: (copy 1): p_u_66, (ref 2): v_u_2, (ref 3): v_u_10, (ref 4): v_u_11, (ref 5): v_u_6, (ref 6): v_u_5, (copy 7): p_u_67, (ref 8): v_u_7, (ref 9): v_u_36, (ref 10): v_u_16, (copy 11): p_u_70, (copy 12): v_u_78 ]]
        p88.Parent = nil
        local v_u_91 = p_u_66._player_blob_manager:get_player_blob()
        local v_u_92 = 0
        local v_u_93 = v_u_2:new()
        local l_Title_0 = p89.PrimaryPart.SurfaceGui.Frame.Title
        local v_u_94 = nil
        local v_u_95 = nil
        local function f_update_ui_elements() --[[ Name: update_ui_elements ]] --[[ Line: 160 ]]
            --[[ Upvalues: (ref 1): v_u_10, (copy 2): v_u_91, (ref 3): v_u_11, (ref 4): v_u_92, (copy 5): v_u_93, (copy 6): l_Title_0, (ref 7): v_u_94, (ref 8): v_u_95 ]]
            local v96 = v_u_10:get_owned_equipment_list(v_u_91)
            v96:remove_if(function(p97) --[[ Line: 162 ]]
                --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_91 ]]
                return v_u_10:ownedid_is_equipped(v_u_91, p97.OwnedID);
            end)
            v96:sort(v_u_11:get_sort_fn_for_playerblob(v_u_91))
            if v_u_92 >= v96:count() then
                v_u_92 = v96:count() - v_u_93:count()
            end;
            if v_u_92 < 0 then
                v_u_92 = 0
            end;
            if v96:count() == 0 then
                l_Title_0.Text = "Owned (None)"
            else
                l_Title_0.Text = string.format("Owned (%d of %d)", math.floor(v_u_92 / v_u_93:count()) + 1, math.floor((v96:count() - 1) / v_u_93:count()) + 1)
            end;
            for v98 = 1, v_u_93:count() do
                local v99 = v_u_93:get(v98)
                local v100 = v98 + v_u_92
                if v100 <= v96:count() then
                    v99:set_owned_obj(v_u_91, v96:get(v100).OwnedID)
                else
                    v99:set_hidden()
                end;
            end;
            if v_u_92 == 0 then
                v_u_94:set_visible(false)
            else
                v_u_94:set_visible(true)
            end;
            if v_u_92 + v_u_93:count() >= v96:count() then
                v_u_95:set_visible(false)
            else
                v_u_95:set_visible(true)
            end;
        end;
        local function _(p101) --[[ Name: increment_owned_list_offset ]] --[[ Line: 206 ]]
            --[[ Upvalues: (ref 1): v_u_92, (copy 2): f_update_ui_elements ]]
            v_u_92 = v_u_92 + p101
            f_update_ui_elements()
        end;
        v_u_94 = p_u_87:add_cycle_element(p_u_66, 1, v_u_6:new(v_u_5:new(p90, p89.PrimaryPart, p89.TopArrowSurface), p_u_67, function() --[[ Line: 214 ]]
            --[[ Upvalues: (ref 1): p_u_66, (ref 2): v_u_7, (copy 3): v_u_93, (ref 4): v_u_92, (copy 5): f_update_ui_elements ]]
            p_u_66._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
            v_u_92 = v_u_92 + -v_u_93:count()
            f_update_ui_elements()
        end))
        v_u_95 = p_u_87:add_cycle_element(p_u_66, 1, v_u_6:new(v_u_5:new(p90, p89.PrimaryPart, p89.BottomArrowSurface), p_u_67, function() --[[ Line: 223 ]]
            --[[ Upvalues: (ref 1): p_u_66, (ref 2): v_u_7, (copy 3): v_u_93, (ref 4): v_u_92, (copy 5): f_update_ui_elements ]]
            p_u_66._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
            v_u_92 = v_u_92 + v_u_93:count()
            f_update_ui_elements()
        end))
        for v102 = 1, 6 do
            local l_Anchors_0 = p89.Anchors[tostring(v102)]
            local v103 = p88:Clone()
            v103.Parent = p89
            local v_u_104 = v_u_36:new(p_u_66, v_u_5:new(p90, p89.PrimaryPart, v103), v_u_16:new(v103):set_stat_icon_left_margin(1), p_u_70)
            v_u_104:add_child_uibutton((p_u_87:add_cycle_element(p_u_66, 1, v_u_6:new(v_u_5:new(v_u_104:get_uichild(), v_u_104:get_uichild():get_child_part(), v103.SelectButton), p_u_67, function() --[[ Line: 244 ]]
                --[[ Upvalues: (copy 1): p_u_87, (copy 2): v_u_91, (copy 3): v_u_104 ]]
                p_u_87:owned_id_selected(v_u_91, v_u_104:get_owned_id())
            end))))
            v_u_104:get_uichild():set_position(l_Anchors_0.Position)
            v_u_78:push_back(v_u_104)
            v_u_93:push_back(v_u_104)
        end;
        f_update_ui_elements()
    end;
    v72.initialize_equipped_section_gear_displays = function(p_u_105, _, p106, p107, p108) --[[ Name: initialize_equipped_section_gear_displays ]] --[[ Line: 257 ]]
        --[[ Upvalues: (copy 1): p_u_66, (ref 2): v_u_9, (ref 3): v_u_36, (ref 4): v_u_5, (ref 5): v_u_16, (copy 6): p_u_70, (ref 7): v_u_10, (ref 8): v_u_6, (copy 9): p_u_67, (ref 10): v_u_7, (copy 11): v_u_78 ]]
        p106.Parent = nil
        local v_u_109 = p_u_66._player_blob_manager:get_player_blob()
        for _, v110 in v_u_9:slot_itr() do
            local l_Anchors_1 = p107.Anchors[v_u_9:slot_to_name(v110)]
            local v111 = p106:Clone()
            v111.Parent = p107
            local v_u_112 = v_u_36:new(p_u_66, v_u_5:new(p108, p107.PrimaryPart, v111), v_u_16:new(v111):set_stat_icon_left_margin(1), p_u_70)
            local v113, _, v114 = v_u_10:get_equippedobj_for_slot(v_u_109, v110)
            if v113 == nil then
                v_u_112:set_empty_slot(v110)
            else
                v_u_112:set_owned_obj(v_u_109, v114)
            end;
            v_u_112:add_child_uibutton((p_u_105:add_cycle_element(p_u_66, 1, v_u_6:new(v_u_5:new(v_u_112:get_uichild(), v_u_112:get_uichild():get_child_part(), v111.SelectButton), p_u_67, function() --[[ Line: 284 ]]
                --[[ Upvalues: (ref 1): p_u_66, (ref 2): v_u_7, (copy 3): p_u_105, (copy 4): v_u_109, (copy 5): v_u_112 ]]
                p_u_66._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
                p_u_105:owned_id_selected(v_u_109, v_u_112:get_owned_id())
            end))))
            v_u_112:get_uichild():set_position(l_Anchors_1.Position)
            v_u_78:push_back(v_u_112)
        end;
    end;
    v72.visual_update = function(p115, p116, p117) --[[ Name: visual_update ]] --[[ Line: 296 ]]
        --[[ Upvalues: (copy 1): v_u_78 ]]
        for v118 = 1, v_u_78:count() do
            v_u_78:get(v118):visual_update(p116, p117)
        end;
        p115:visual_update_base(p116, p117)
    end;
    v72.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 303 ]]
        --[[ Upvalues: (ref 1): v_u_73 ]]
        v_u_73:Destroy()
    end;
    v72.layout = function(_) --[[ Name: layout ]] --[[ Line: 307 ]]
        --[[ Upvalues: (ref 1): v_u_76, (ref 2): v_u_77, (copy 3): v_u_78 ]]
        v_u_76:layout()
        v_u_77:layout()
        for v119 = 1, v_u_78:count() do
            v_u_78:get(v119):layout()
        end;
    end;
    v72.set_alpha = function(_, p120) --[[ Name: set_alpha ]] --[[ Line: 315 ]]
        --[[ Upvalues: (ref 1): v_u_74, (ref 2): v_u_1, (ref 3): v_u_73 ]]
        if v_u_74 ~= p120 then
            v_u_74 = p120
            v_u_1:r_set_alpha(v_u_73, v_u_74)
        end;
    end;
    v72.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 321 ]]
        --[[ Upvalues: (ref 1): v_u_74 ]]
        return v_u_74;
    end;
    v72.set_scale = function(_, p121) --[[ Name: set_scale ]] --[[ Line: 322 ]]
        --[[ Upvalues: (ref 1): v_u_75, (ref 2): v_u_76, (ref 3): v_u_77 ]]
        v_u_75 = p121
        v_u_76:set_scale(p121)
        v_u_77:set_scale(p121)
    end;
    v72.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 327 ]]
        --[[ Upvalues: (ref 1): v_u_75 ]]
        return v_u_75;
    end;
    v72.get_native_size = function(p122) --[[ Name: get_native_size ]] --[[ Line: 328 ]]
        return p122._native_size;
    end;
    v72.get_size = function(p123) --[[ Name: get_size ]] --[[ Line: 331 ]]
        return p123._size;
    end;
    v72.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 334 ]]
        --[[ Upvalues: (ref 1): v_u_73 ]]
        return v_u_73.PrimaryPart.Position;
    end;
    v72.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 337 ]]
        --[[ Upvalues: (ref 1): v_u_73 ]]
        return v_u_73.PrimaryPart.SurfaceGui;
    end;
    v72:cons()
    return v72;
end;
v_u_65.show_delete_gear_menu = function(_, p_u_124, p_u_125, p_u_126) --[[ Name: show_delete_gear_menu ]] --[[ Line: 427 ]]
    --[[ Upvalues: (copy 1): v_u_65, (copy 2): v_u_10, (copy 3): v_u_12, (ref 4): v_u_15, (copy 5): v_u_7 ]]
    p_u_124._menus:push_menu(v_u_65:new(p_u_124, p_u_125, p_u_124._menus, function(p127, p_u_128) --[[ Line: 432 ]]
        --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_12, (copy 3): p_u_124, (ref 4): v_u_15, (copy 5): p_u_125, (copy 6): p_u_126, (ref 7): v_u_7 ]]
        local v129 = v_u_10:playerblob_ownedid_to_equipmentid(p127, p_u_128)
        if v129 ~= nil then
            p_u_124._menus:push_menu(v_u_15:new(p_u_124, p_u_125, p_u_124._menus):set_text("Confirm Delete", (string.format("Are you sure you want to delete \"%s\"?", v_u_12:singleton():get_equipment_for_id(v129):get_name()))):set_okay_button_fn(function() --[[ Line: 437 ]]
                --[[ Upvalues: (ref 1): p_u_124, (ref 2): v_u_15, (ref 3): p_u_125, (copy 4): p_u_128, (ref 5): p_u_126, (ref 6): v_u_7 ]]
                local v_u_130 = p_u_124._menus:push_menu(v_u_15:new(p_u_124, p_u_125, p_u_124._menus):set_text("Trashing...", ""):set_close_button_visible(false))
                p_u_124._shop_local_protocol:try_delete_gear(p_u_128, function(p131, p132) --[[ Line: 439 ]]
                    --[[ Upvalues: (ref 1): p_u_124, (copy 2): v_u_130, (ref 3): v_u_15, (ref 4): p_u_125, (ref 5): p_u_126, (ref 6): v_u_7 ]]
                    if p131 == true then
                        p_u_124._player_blob_manager:do_sync(function(_) --[[ Line: 446 ]]
                            --[[ Upvalues: (ref 1): p_u_124, (ref 2): v_u_15, (ref 3): p_u_125, (ref 4): p_u_126, (ref 5): v_u_130, (ref 6): v_u_7 ]]
                            p_u_124._menus:push_menu(v_u_15:new(p_u_124, p_u_125, p_u_124._menus):set_text("Deleted!", "This gear has been removed from your inventory."):set_on_close_fn(function() --[[ Line: 450 ]]
                                --[[ Upvalues: (ref 1): p_u_126 ]]
                                if p_u_126 then
                                    p_u_126()
                                end;
                            end))
                            p_u_124._menus:remove_menu(v_u_130)
                            p_u_124._sfx_manager:play_sfx(v_u_7.SFX_FAIL)
                        end)
                    else
                        p_u_124._menus:remove_menu(v_u_130)
                        p_u_124._menus:push_menu(v_u_15:new(p_u_124, p_u_125, p_u_124._menus):set_text("Could not trash gear.", p132))
                    end;
                end)
            end))
        end;
    end, function(p133, p134) --[[ Line: 461 ]]
        --[[ Upvalues: (ref 1): v_u_10 ]]
        return v_u_10:ownedid_is_equipped(p133, p134) ~= true;
    end))
end;
v_u_65.show_upgrade_edit_menu = function(_, p_u_135, p_u_136) --[[ Name: show_upgrade_edit_menu ]] --[[ Line: 467 ]]
    --[[ Upvalues: (copy 1): v_u_65, (ref 2): v_u_14, (copy 3): v_u_10 ]]
    p_u_135._menus:push_menu(v_u_65:new(p_u_135, p_u_136, p_u_135._menus, function(_, p137) --[[ Line: 472 ]]
        --[[ Upvalues: (copy 1): p_u_135, (ref 2): v_u_14, (copy 3): p_u_136 ]]
        p_u_135._menus:push_menu(v_u_14:new(p_u_135, p_u_136, p_u_135._menus, p137))
    end, function(p138, p139) --[[ Line: 475 ]]
        --[[ Upvalues: (ref 1): v_u_10 ]]
        return v_u_10:get_ownedid_upgrade_count(p138, p139) > 0;
    end))
end;
return v_u_65;
