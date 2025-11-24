-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:16 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v2 = require(game.ReplicatedStorage.Shared.SPDict)
local v3 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_4 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_6 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_7 = require(game.ReplicatedStorage.Local.DebugOut)
local v_u_8 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_9 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_10 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_11 = require(game.ReplicatedStorage.Shared.SPMultiDict)
require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
local v_u_12 = require(game.ReplicatedStorage.Tutorial.GearCraftingTutorialInfo)
local v13 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_14 = nil
local v_u_15 = nil
local v_u_16 = nil
local v_u_17 = nil
local v_u_18 = nil
local v_u_19 = nil
local v_u_20 = nil
local v_u_21 = nil
v13:require_client(function() --[[ Line: 25 ]]
    --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_15, (ref 3): v_u_16, (ref 4): v_u_17, (ref 5): v_u_18, (ref 6): v_u_19, (ref 7): v_u_20, (ref 8): v_u_21 ]]
    v_u_14 = require(game.ReplicatedStorage.Lobby.Menus.GearEquipV2UI)
    v_u_15 = require(game.ReplicatedStorage.Lobby.Menus.GearShopUI)
    v_u_16 = require(game.ReplicatedStorage.Lobby.Menus.CraftingUI)
    v_u_17 = require(game.ReplicatedStorage.Lobby.Menus.CraftingGatchaUI)
    v_u_18 = require(game.ReplicatedStorage.Lobby.Menus.MarketplaceUI)
    v_u_19 = require(game.ReplicatedStorage.Lobby.UI.CraftingUITabGearUpgrades)
    v_u_20 = require(game.ReplicatedStorage.Lobby.UI.CraftingUITabGear)
    v_u_21 = require(game.ReplicatedStorage.Lobby.Menus.EquipUI)
end)
local v22 = {}
local v_u_23 = {
    ["Page1"] = 1,
    ["Page2"] = 2,
    ["Page3"] = 3,
    ["Page4"] = 4,
    ["Page5"] = 5,
    ["Page6"] = 6
}
local v_u_24 = v2:new():add_table({
    [v_u_23.Page1] = "http://www.roblox.com/asset/?id=6276691757",
    [v_u_23.Page2] = "http://www.roblox.com/asset/?id=6276692001",
    [v_u_23.Page3] = "http://www.roblox.com/asset/?id=6276692142",
    [v_u_23.Page4] = "http://www.roblox.com/asset/?id=6276692395",
    [v_u_23.Page5] = "http://www.roblox.com/asset/?id=6276692605",
    [v_u_23.Page6] = "http://www.roblox.com/asset/?id=6276692854"
})
local v_u_25 = v3:new()
v22.active_instances = function(_) --[[ Name: active_instances ]] --[[ Line: 56 ]]
    --[[ Upvalues: (copy 1): v_u_25 ]]
    return v_u_25;
end;
local l_Page1_0 = v_u_23.Page1
v22.new = function(_, p_u_26, p_u_27, p_u_28) --[[ Name: new ]] --[[ Line: 60 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_11, (copy 3): v_u_1, (copy 4): v_u_9, (copy 5): v_u_6, (copy 6): v_u_5, (copy 7): v_u_8, (copy 8): v_u_23, (ref 9): v_u_15, (ref 10): v_u_21, (ref 11): v_u_17, (ref 12): v_u_18, (ref 13): v_u_16, (ref 14): v_u_19, (ref 15): v_u_20, (copy 16): v_u_25, (ref 17): l_Page1_0, (copy 18): v_u_10, (copy 19): v_u_12, (copy 20): v_u_7, (copy 21): v_u_24 ]]
    local v29 = v_u_4:new(p_u_27, p_u_28)
    local v_u_30 = nil
    local v_u_31 = 1
    local v_u_32 = 1
    local v_u_33 = nil
    local v_u_34 = nil
    local v_u_35 = nil
    local v_u_36 = nil
    local v_u_37 = v_u_11:new()
    v29.cons = function(p_u_38) --[[ Name: cons ]] --[[ Line: 74 ]]
        --[[ Upvalues: (ref 1): v_u_30, (ref 2): v_u_1, (ref 3): v_u_9, (ref 4): v_u_34, (ref 5): v_u_33, (ref 6): v_u_35, (copy 7): p_u_26, (ref 8): v_u_6, (ref 9): v_u_5, (copy 10): p_u_27, (ref 11): v_u_8, (ref 12): v_u_36, (copy 13): p_u_28, (copy 14): v_u_37, (ref 15): v_u_23, (ref 16): v_u_15, (ref 17): v_u_21, (ref 18): v_u_17, (ref 19): v_u_18, (ref 20): v_u_16, (ref 21): v_u_19, (ref 22): v_u_20, (ref 23): v_u_25 ]]
        v_u_30 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.GearCraftingTutorialUI:Clone()
        v_u_30.Name = v_u_1:gen_name(v_u_30.Name)
        v_u_30.Parent = v_u_9:get_world_ui_folder()
        p_u_38._native_size = v_u_30.PrimaryPart.Size
        p_u_38._size = p_u_38._native_size
        v_u_34 = v_u_30.MainSurface.SurfaceGui.Frame.Frame.LoadingDisplay
        v_u_33 = v_u_30.MainSurface.SurfaceGui.Frame.Frame.Image
        v_u_35 = p_u_38:add_cycle_element(p_u_26, 1, v_u_6:new(v_u_5:new(p_u_38, v_u_30.PrimaryPart, v_u_30.ArrowLeft), p_u_27, function() --[[ Line: 88 ]]
            --[[ Upvalues: (ref 1): p_u_26, (ref 2): v_u_8, (copy 3): p_u_38 ]]
            p_u_26._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            p_u_38:list_scroll_by(-1)
        end):set_passive_anim())
        v_u_36 = p_u_38:add_cycle_element(p_u_26, 1, v_u_6:new(v_u_5:new(p_u_38, v_u_30.PrimaryPart, v_u_30.ArrowRight), p_u_27, function() --[[ Line: 97 ]]
            --[[ Upvalues: (ref 1): p_u_26, (ref 2): v_u_8, (copy 3): p_u_38 ]]
            p_u_26._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            p_u_38:list_scroll_by(1)
        end):set_passive_anim())
        p_u_38:add_cycle_element(p_u_26, 1, v_u_6:new(v_u_5:new(p_u_38, v_u_30.PrimaryPart, v_u_30.BackButtonSurface), p_u_27, function() --[[ Line: 106 ]]
            --[[ Upvalues: (ref 1): p_u_26, (ref 2): v_u_8, (ref 3): p_u_28, (copy 4): p_u_38 ]]
            p_u_26._sfx_manager:play_sfx(v_u_8.SFX_MENU_CLOSE)
            p_u_28:remove_menu(p_u_38)
        end))
        v_u_37:push_back_to(v_u_23.Page1, p_u_38:add_cycle_element(p_u_26, 1, v_u_6:new(v_u_5:new(p_u_38, v_u_30.PrimaryPart, v_u_30.Buttons.GearShopButton), p_u_27, function() --[[ Line: 115 ]]
            --[[ Upvalues: (ref 1): p_u_26, (ref 2): v_u_8, (ref 3): p_u_28, (ref 4): v_u_15, (ref 5): p_u_27 ]]
            p_u_26._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            p_u_28:push_menu(v_u_15:new(p_u_26, p_u_27, p_u_28))
        end)))
        v_u_37:push_back_to(v_u_23.Page1, p_u_38:add_cycle_element(p_u_26, 1, v_u_6:new(v_u_5:new(p_u_38, v_u_30.PrimaryPart, v_u_30.Buttons.GearButton), p_u_27, function() --[[ Line: 124 ]]
            --[[ Upvalues: (ref 1): p_u_26, (ref 2): v_u_8, (ref 3): p_u_28, (ref 4): v_u_21, (ref 5): p_u_27 ]]
            p_u_26._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            p_u_28:push_menu(v_u_21:new(p_u_26, p_u_27, p_u_28))
        end)))
        v_u_37:push_back_to(v_u_23.Page4, p_u_38:add_cycle_element(p_u_26, 1, v_u_6:new(v_u_5:new(p_u_38, v_u_30.PrimaryPart, v_u_30.Buttons.NoteMachineButton), p_u_27, function() --[[ Line: 133 ]]
            --[[ Upvalues: (ref 1): p_u_26, (ref 2): v_u_8, (ref 3): p_u_28, (ref 4): v_u_17, (ref 5): p_u_27 ]]
            p_u_26._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            p_u_28:push_menu(v_u_17:new(p_u_26, p_u_27, p_u_28))
        end)))
        v_u_37:push_back_to(v_u_23.Page4, p_u_38:add_cycle_element(p_u_26, 1, v_u_6:new(v_u_5:new(p_u_38, v_u_30.PrimaryPart, v_u_30.Buttons.MarketplaceButton), p_u_27, function() --[[ Line: 142 ]]
            --[[ Upvalues: (ref 1): p_u_26, (ref 2): v_u_8, (ref 3): p_u_28, (ref 4): v_u_18, (ref 5): p_u_27 ]]
            p_u_26._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            p_u_28:push_menu(v_u_18:new(p_u_26, p_u_27, p_u_28))
        end)))
        v_u_37:push_back_to(v_u_23.Page4, p_u_38:add_cycle_element(p_u_26, 1, v_u_6:new(v_u_5:new(p_u_38, v_u_30.PrimaryPart, v_u_30.Buttons.CraftButtonUpgrade), p_u_27, function() --[[ Line: 151 ]]
            --[[ Upvalues: (ref 1): p_u_26, (ref 2): v_u_8, (ref 3): p_u_28, (ref 4): v_u_16, (ref 5): p_u_27, (ref 6): v_u_19 ]]
            p_u_26._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            p_u_28:push_menu(v_u_16:new(p_u_26, p_u_27, p_u_28, v_u_19.Tab))
        end)))
        v_u_37:push_back_to(v_u_23.Page5, p_u_38:add_cycle_element(p_u_26, 1, v_u_6:new(v_u_5:new(p_u_38, v_u_30.PrimaryPart, v_u_30.Buttons.CraftButtonGear), p_u_27, function() --[[ Line: 160 ]]
            --[[ Upvalues: (ref 1): p_u_26, (ref 2): v_u_8, (ref 3): p_u_28, (ref 4): v_u_16, (ref 5): p_u_27, (ref 6): v_u_20 ]]
            p_u_26._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            p_u_28:push_menu(v_u_16:new(p_u_26, p_u_27, p_u_28, v_u_20.Tab))
        end)))
        p_u_38:list_scroll_by(0)
        p_u_38:transition_update_visual(0)
        p_u_38:layout()
        v_u_25:push_back(p_u_38)
    end;
    v29.go_to_last_page = function(p39) --[[ Name: go_to_last_page ]] --[[ Line: 173 ]]
        --[[ Upvalues: (ref 1): l_Page1_0, (ref 2): v_u_23 ]]
        l_Page1_0 = v_u_23.Page6
        p39:list_scroll_by(0)
        return p39;
    end;
    v29.can_go_to_next_page = function(_, p40) --[[ Name: can_go_to_next_page ]] --[[ Line: 179 ]]
        --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_23, (copy 3): p_u_26, (ref 4): v_u_12 ]]
        if v_u_10:test_enum_member(p40 + 1, v_u_23) == true then
            local v41 = p_u_26._player_blob_manager:get_player_blob()
            if p40 == v_u_23.Page1 then
                return v_u_12:has_any_equipped_gear(v41);
            elseif p40 == v_u_23.Page4 then
                return v_u_12:has_any_gear_upgrades(v41);
            else
                return p40 ~= v_u_23.Page5 and true or v_u_12:playerblob_owns_any_tutorial_gear(v41);
            end;
        else
            return false;
        end;
    end;
    v29.list_scroll_by = function(p42, p43) --[[ Name: list_scroll_by ]] --[[ Line: 197 ]]
        --[[ Upvalues: (ref 1): l_Page1_0, (ref 2): v_u_10, (ref 3): v_u_23, (ref 4): v_u_7, (ref 5): v_u_24, (ref 6): v_u_33, (ref 7): v_u_35, (ref 8): v_u_36, (copy 9): v_u_37 ]]
        local v44 = l_Page1_0 + p43
        if v_u_10:test_enum_member(v44, v_u_23) == true then
            l_Page1_0 = v44
            if v_u_24:contains(l_Page1_0) then
                v_u_33.Image = v_u_24:get(l_Page1_0)
            end;
            v_u_35:set_visible(v_u_10:test_enum_member(l_Page1_0 - 1, v_u_23))
            local v45 = v_u_36
            local v46 = v_u_10:test_enum_member(l_Page1_0 + 1, v_u_23)
            if v46 then
                v46 = p42:can_go_to_next_page(l_Page1_0)
            end;
            v45:set_visible(v46)
            for v47, v48 in v_u_37:key_itr() do
                for _, v49 in v48:key_itr() do
                    v49:set_visible(l_Page1_0 == v47, true)
                end;
            end;
        else
            v_u_7:warnf("GearCratingTutorialUI list_scroll_by invalid(%s)", v44)
        end;
    end;
    v29.on_refocus = function(p50) --[[ Name: on_refocus ]] --[[ Line: 219 ]]
        p50:list_scroll_by(0)
    end;
    v29.behaviour_update = function(p51, p52, _) --[[ Name: behaviour_update ]] --[[ Line: 223 ]]
        --[[ Upvalues: (copy 1): p_u_26, (ref 2): v_u_34, (ref 3): v_u_33 ]]
        p51:behaviour_update_base(p52, p_u_26)
        v_u_34.Visible = not v_u_33.IsLoaded
    end;
    v29.do_remove = function(p53, _) --[[ Name: do_remove ]] --[[ Line: 228 ]]
        --[[ Upvalues: (ref 1): v_u_30, (ref 2): v_u_25 ]]
        v_u_30:Destroy()
        v_u_25:remove(p53)
    end;
    v29.layout = function(p54) --[[ Name: layout ]] --[[ Line: 233 ]]
        --[[ Upvalues: (copy 1): p_u_27, (ref 2): v_u_32, (ref 3): v_u_30 ]]
        p54:opt_rescale_to_max_nxy(p_u_27, 0.8, 0.8, v_u_32)
        local v55, v56 = p54:opt_update_cframe_params(p_u_27, {
            ["PositionNXY"] = Vector2.new(0.5, 0.5),
            ["OffsetXYZ"] = p54:anchored_offset(0.5, 0.5),
            ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
        })
        if v55 == true then
            v_u_30:SetPrimaryPartCFrame(v56)
        end;
    end;
    v29.set_alpha = function(_, p57) --[[ Name: set_alpha ]] --[[ Line: 245 ]]
        --[[ Upvalues: (ref 1): v_u_31, (ref 2): v_u_1, (ref 3): v_u_30 ]]
        if v_u_31 ~= p57 then
            v_u_31 = p57
            v_u_1:r_set_alpha(v_u_30, v_u_31)
        end;
    end;
    v29.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 251 ]]
        --[[ Upvalues: (ref 1): v_u_31 ]]
        return v_u_31;
    end;
    v29.set_scale = function(_, p58) --[[ Name: set_scale ]] --[[ Line: 252 ]]
        --[[ Upvalues: (ref 1): v_u_32 ]]
        v_u_32 = p58
    end;
    v29.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 253 ]]
        --[[ Upvalues: (ref 1): v_u_32 ]]
        return v_u_32;
    end;
    v29.get_native_size = function(p59) --[[ Name: get_native_size ]] --[[ Line: 255 ]]
        return p59._native_size;
    end;
    v29.get_size = function(p60) --[[ Name: get_size ]] --[[ Line: 258 ]]
        return p60._size;
    end;
    v29.set_size = function(p61, p62) --[[ Name: set_size ]] --[[ Line: 261 ]]
        --[[ Upvalues: (ref 1): v_u_30 ]]
        p61._size = p62
        v_u_30.PrimaryPart.Size = Vector3.new(p62.X, p62.Y, 0)
    end;
    v29.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 265 ]]
        --[[ Upvalues: (ref 1): v_u_30 ]]
        return v_u_30.PrimaryPart.Position;
    end;
    v29.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 268 ]]
        --[[ Upvalues: (ref 1): v_u_30 ]]
        return v_u_30.PrimaryPart.SurfaceGui;
    end;
    v29:cons()
    return v29;
end;
return v22;
