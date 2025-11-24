-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:44 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_4 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_6 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_7 = require(game.ReplicatedStorage.Local.DebugOut)
local v_u_8 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_9 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
require(game.ReplicatedStorage.Lobby.UI.SPUITextInput)
require(game.ReplicatedStorage.Shared.InputUtil)
local v_u_10 = require(game.ReplicatedStorage.Crafting.CraftDatabase)
require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_11 = require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
local v_u_12 = require(game.ReplicatedStorage.Crafting.CraftingMaterialBase)
local v_u_13 = require(game.ReplicatedStorage.Lobby.UI.CraftingUISearchSection)
local v_u_14 = require(game.ReplicatedStorage.Lobby.UI.CraftingUIListElement)
return {
    ["new"] = function(_, p_u_15, p_u_16, p_u_17, p_u_18) --[[ Name: new ]] --[[ Line: 24 ]]
        --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_3, (copy 3): v_u_1, (copy 4): v_u_9, (copy 5): v_u_5, (copy 6): v_u_6, (copy 7): v_u_8, (copy 8): v_u_14, (copy 9): v_u_11, (copy 10): v_u_13, (copy 11): v_u_2, (copy 12): v_u_10, (copy 13): v_u_7, (copy 14): v_u_12 ]]
        local v19 = v_u_4:new(p_u_16, p_u_17)
        local v_u_20 = nil
        local v_u_21 = nil
        local v_u_22 = v_u_3:new()
        local v_u_23 = 0
        local v_u_24 = nil
        local v_u_25 = nil
        local v_u_26 = -1
        local v_u_27 = 0
        local v_u_28 = nil
        local v_u_29 = nil
        local v_u_30 = nil
        local v_u_31 = nil
        local v_u_32 = nil
        local v_u_33 = nil
        local v_u_34 = nil
        local v_u_35 = nil
        v19.cons = function(p_u_36) --[[ Name: cons ]] --[[ Line: 40 ]]
            --[[ Upvalues: (ref 1): v_u_20, (ref 2): v_u_1, (ref 3): v_u_9, (ref 4): v_u_31, (ref 5): v_u_32, (ref 6): v_u_33, (ref 7): v_u_34, (ref 8): v_u_35, (ref 9): v_u_21, (ref 10): v_u_5, (copy 11): p_u_15, (ref 12): v_u_6, (copy 13): p_u_16, (copy 14): p_u_17, (ref 15): v_u_8, (ref 16): v_u_25, (ref 17): v_u_24, (ref 18): v_u_29, (ref 19): v_u_28, (ref 20): v_u_30 ]]
            v_u_20 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.MaterialSelectUI:Clone()
            v_u_20.Name = v_u_1:gen_name(v_u_20.Name)
            v_u_20.Parent = v_u_9:get_world_ui_folder()
            p_u_36._native_size = v_u_20.PrimaryPart.Size
            p_u_36._size = p_u_36._native_size
            local l_Frame_0 = v_u_20.MainSurface.SurfaceGui.Frame
            v_u_31 = l_Frame_0.SelectedInfoSection.IconFrame.Icon
            v_u_32 = l_Frame_0.SelectedInfoSection.OwnedDisplay
            v_u_33 = l_Frame_0.SelectedInfoSection.SelectedDisplay
            v_u_34 = l_Frame_0.SelectedInfoSection.NameDisplay
            v_u_35 = l_Frame_0.SelectedInfoSection.DescriptionDisplay
            v_u_21 = v_u_5:new(p_u_36, v_u_20.PrimaryPart, v_u_20.InventoryItemHighlight)
            v_u_21:set_sgui(v_u_21:get_child_part().SurfaceGui)
            p_u_36:add_cycle_element(p_u_15, 1, v_u_6:new(v_u_5:new(p_u_36, v_u_20.PrimaryPart, v_u_20.BackButtonSurface), p_u_16, function() --[[ Line: 61 ]]
                --[[ Upvalues: (ref 1): p_u_17, (copy 2): p_u_36, (ref 3): p_u_15, (ref 4): v_u_8 ]]
                p_u_17:remove_menu(p_u_36)
                p_u_15._sfx_manager:play_sfx(v_u_8.SFX_MENU_CLOSE)
            end))
            v_u_25 = p_u_36:add_cycle_element(p_u_15, 1, v_u_6:new(v_u_5:new(p_u_36, v_u_20.PrimaryPart, v_u_20.BottomArrowSurface), p_u_16, function() --[[ Line: 69 ]]
                --[[ Upvalues: (ref 1): p_u_15, (ref 2): v_u_8, (copy 3): p_u_36 ]]
                p_u_15._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
                p_u_36:page_increment(1)
            end))
            v_u_24 = p_u_36:add_cycle_element(p_u_15, 1, v_u_6:new(v_u_5:new(p_u_36, v_u_20.PrimaryPart, v_u_20.TopArrowSurface), p_u_16, function() --[[ Line: 78 ]]
                --[[ Upvalues: (ref 1): p_u_15, (ref 2): v_u_8, (copy 3): p_u_36 ]]
                p_u_15._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
                p_u_36:page_increment(-1)
            end))
            v_u_29 = p_u_36:add_cycle_element(p_u_15, 1, v_u_6:new(v_u_5:new(p_u_36, v_u_20.PrimaryPart, v_u_20.LeftArrowSurface), p_u_16, function() --[[ Line: 87 ]]
                --[[ Upvalues: (ref 1): p_u_15, (ref 2): v_u_8, (copy 3): p_u_36 ]]
                p_u_15._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
                p_u_36:selection_increment(-1)
            end))
            v_u_28 = p_u_36:add_cycle_element(p_u_15, 1, v_u_6:new(v_u_5:new(p_u_36, v_u_20.PrimaryPart, v_u_20.RightArrowSurface), p_u_16, function() --[[ Line: 96 ]]
                --[[ Upvalues: (ref 1): p_u_15, (ref 2): v_u_8, (copy 3): p_u_36 ]]
                p_u_15._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
                p_u_36:selection_increment(1)
            end))
            v_u_30 = p_u_36:add_cycle_element(p_u_15, 1, v_u_6:new(v_u_5:new(p_u_36, v_u_20.PrimaryPart, v_u_20.OkayButtonSurface), p_u_16, function() --[[ Line: 105 ]]
                --[[ Upvalues: (ref 1): p_u_15, (ref 2): v_u_8, (copy 3): p_u_36 ]]
                p_u_15._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN)
                p_u_36:confirm_button_pressed()
            end):set_passive_anim())
            p_u_36:setup_list_elements()
            p_u_36:transition_update_visual(0)
            p_u_36:layout()
        end;
        v19.setup_list_elements = function(p37) --[[ Name: setup_list_elements ]] --[[ Line: 117 ]]
            --[[ Upvalues: (ref 1): v_u_20, (ref 2): v_u_3, (ref 3): v_u_14, (ref 4): v_u_5, (copy 5): p_u_16, (copy 6): p_u_15, (copy 7): v_u_22 ]]
            local l_InventoryItemProto_0 = v_u_20.InventoryItemProto
            l_InventoryItemProto_0.Parent = nil
            local v38 = v_u_3:new()
            for v39 = 1, 12 do
                v38:push_back(v_u_20.Anchors:FindFirstChild(string.format("Anchor%d", v39)))
            end;
            for v40 = 1, v38:count() do
                local v41 = v38:get(v40)
                local v42 = l_InventoryItemProto_0:Clone()
                v42.Name = string.format("CraftingUIListElement(%d)", v40)
                v42.Parent = v_u_20
                v42.Position = v41.Position
                local v43 = v_u_14:new(v_u_5:new(p37, v_u_20.PrimaryPart, v42), p_u_16, p37, v40)
                p37:add_cycle_element(p_u_15, 1, v43)
                v_u_22:push_back(v43)
            end;
            p37:update_display()
        end;
        local function v_u_44(_) --[[ Line: 146 ]]
            return false;
        end;
        v19.set_fn_material_ids_filter = function(p45, p46) --[[ Name: set_fn_material_ids_filter ]] --[[ Line: 149 ]]
            --[[ Upvalues: (ref 1): v_u_44 ]]
            v_u_44 = p46
            p45:update_display()
            return p45;
        end;
        local v_u_47 = nil
        v19.set_fn_update_owned_materials_dict = function(p48, p49) --[[ Name: set_fn_update_owned_materials_dict ]] --[[ Line: 157 ]]
            --[[ Upvalues: (ref 1): v_u_47 ]]
            v_u_47 = p49
            p48:update_display()
            return p48;
        end;
        v19.get_ids_list = function(_) --[[ Name: get_ids_list ]] --[[ Line: 164 ]]
            --[[ Upvalues: (copy 1): p_u_15, (ref 2): v_u_11, (ref 3): v_u_3, (ref 4): v_u_44, (ref 5): v_u_13 ]]
            local v50 = v_u_11:get_owned_crafting_materials((p_u_15._player_blob_manager:get_player_blob())):key_list()
            v_u_3:remove_if(v50, v_u_44)
            v50:sort(function(p51, p52) --[[ Line: 170 ]]
                --[[ Upvalues: (ref 1): v_u_13 ]]
                return v_u_13:materialid_get_type_sort_value(p52) > v_u_13:materialid_get_type_sort_value(p51) == false and -1 or 1;
            end)
            return v50;
        end;
        v19.update_display = function(p53) --[[ Name: update_display ]] --[[ Line: 178 ]]
            --[[ Upvalues: (copy 1): p_u_15, (ref 2): v_u_11, (ref 3): v_u_47, (ref 4): v_u_2, (copy 5): v_u_22, (ref 6): v_u_23, (ref 7): v_u_26, (ref 8): v_u_27, (ref 9): v_u_10, (ref 10): v_u_7, (ref 11): v_u_24, (ref 12): v_u_25, (ref 13): v_u_31, (ref 14): v_u_33, (ref 15): v_u_34, (ref 16): v_u_35, (ref 17): v_u_32, (ref 18): v_u_28, (ref 19): v_u_29, (ref 20): v_u_30, (ref 21): v_u_21, (ref 22): v_u_1, (ref 23): v_u_12 ]]
            p53:clear_list()
            local v_u_54 = v_u_11:get_owned_crafting_materials((p_u_15._player_blob_manager:get_player_blob()))
            local v55 = p53:get_ids_list()
            if v_u_47 then
                v_u_47(v_u_54)
                v55:remove_if(function(p56) --[[ Line: 187 ]]
                    --[[ Upvalues: (ref 1): v_u_2, (copy 2): v_u_54 ]]
                    return v_u_2:counter_get(v_u_54, p56) <= 0;
                end)
            end;
            for v57 = 1, v_u_22:count() do
                local v58 = v_u_22:get(v57)
                local v59 = v_u_23 * v_u_22:count() + v57
                if v59 <= v55:count() then
                    local v60 = v55:get(v59)
                    local v61 = v_u_54:get(v60)
                    local v62 = v61 == nil and 0 or v61
                    if v62 > 0 then
                        if v60 == v_u_26 then
                            v62 = v62 - v_u_27
                        end;
                        if v62 >= 0 then
                            v58:set_info(v60, v_u_10:singleton():get_material_icon(v60), v62)
                            v58:set_visible(true)
                        else
                            v_u_7:warnf("MaterialSelectUI unexpected behaviour2: material(%d) count(%d)", v60, v62)
                            v58:set_visible(false)
                        end;
                    else
                        v_u_7:warnf("MaterialSelectUI unexpected behaviour1: material(%d) count(%d)", v60, v62)
                    end;
                end;
            end;
            v_u_24:set_visible(p53:can_page_up())
            v_u_25:set_visible(p53:can_page_down())
            if v_u_10:singleton():contains_material(v_u_26) then
                v_u_31.Image = v_u_10:singleton():get_material_icon(v_u_26)
                v_u_33.Text = tostring(v_u_27)
                v_u_34.Text = v_u_10:singleton():get_material_name(v_u_26)
                v_u_34.TextColor3 = v_u_10:singleton():tier_get_color(v_u_10:singleton():get_material_tier(v_u_26))
                v_u_35.Text = v_u_10:singleton():get_material_description(v_u_26)
                if v_u_54:contains(v_u_26) then
                    v_u_32.Text = v_u_54:get(v_u_26) - v_u_27
                    v_u_28:set_visible(v_u_27 < v_u_54:get(v_u_26))
                    v_u_29:set_visible(v_u_27 > 1)
                    v_u_30:set_visible(v_u_27 > 0)
                else
                    v_u_32.Text = "-"
                    v_u_28:set_visible(false)
                    v_u_29:set_visible(false)
                    v_u_30:set_visible(false)
                end;
                v_u_21:set_visible(false)
                for v63 = 1, v_u_22:count() do
                    local v64 = v_u_22:get(v63)
                    if v64:get_enabled() and v64:get_data() == v_u_26 then
                        v64:set_highlighted(true)
                        v_u_21:set_visible(true)
                        v_u_21:set_position_scaled_offset(v64:get_pos(), Vector2.new(0, -0.15))
                    else
                        v64:set_highlighted(false)
                    end;
                end;
            else
                v_u_31.Image = v_u_1:transparent_assetid()
                v_u_32.Text = "-"
                v_u_33.Text = "-"
                v_u_34.Text = "Select Material"
                v_u_34.TextColor3 = v_u_10:singleton():tier_get_color(v_u_12.Tier.T1)
                v_u_35.Text = ""
                v_u_28:set_visible(false)
                v_u_29:set_visible(false)
                v_u_30:set_visible(false)
                v_u_21:set_visible(false)
                for v65 = 1, v_u_22:count() do
                    v_u_22:get(v65):set_highlighted(false)
                end;
            end;
        end;
        v19.selection_increment = function(p66, p67) --[[ Name: selection_increment ]] --[[ Line: 278 ]]
            --[[ Upvalues: (ref 1): v_u_27, (copy 2): v_u_22, (ref 3): v_u_26 ]]
            v_u_27 = v_u_27 + p67
            for v68 = 1, v_u_22:count() do
                local v69 = v_u_22:get(v68)
                if v69:get_enabled() and v69:get_data() == v_u_26 then
                    v69:trigger_element_visual()
                end;
            end;
            p66:update_display()
        end;
        v19.confirm_button_pressed = function(p70) --[[ Name: confirm_button_pressed ]] --[[ Line: 289 ]]
            --[[ Upvalues: (copy 1): p_u_18, (ref 2): v_u_26, (ref 3): v_u_27, (copy 4): p_u_17 ]]
            p_u_18(v_u_26, v_u_27)
            p_u_17:remove_menu(p70)
        end;
        v19.list_element_pressed = function(p71, _, _, p72) --[[ Name: list_element_pressed ]] --[[ Line: 294 ]]
            --[[ Upvalues: (copy 1): p_u_15, (ref 2): v_u_8, (ref 3): v_u_26, (ref 4): v_u_27 ]]
            p_u_15._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            v_u_26 = p72
            v_u_27 = 1
            p71:update_display()
        end;
        v19.page_increment = function(p73, p74) --[[ Name: page_increment ]] --[[ Line: 301 ]]
            --[[ Upvalues: (ref 1): v_u_23 ]]
            v_u_23 = v_u_23 + p74
            p73:update_display()
        end;
        v19.can_page_up = function(_) --[[ Name: can_page_up ]] --[[ Line: 305 ]]
            --[[ Upvalues: (ref 1): v_u_23 ]]
            return v_u_23 > 0;
        end;
        v19.reset_page = function(_) --[[ Name: reset_page ]] --[[ Line: 306 ]]
            --[[ Upvalues: (ref 1): v_u_23 ]]
            v_u_23 = 0
        end;
        v19.can_page_down = function(p75) --[[ Name: can_page_down ]] --[[ Line: 307 ]]
            --[[ Upvalues: (ref 1): v_u_23, (copy 2): v_u_22 ]]
            return (v_u_23 + 1) * v_u_22:count() < p75:get_ids_list():count();
        end;
        v19.clear_list = function(_) --[[ Name: clear_list ]] --[[ Line: 309 ]]
            --[[ Upvalues: (copy 1): v_u_22, (ref 2): v_u_21 ]]
            for v76 = 1, v_u_22:count() do
                v_u_22:get(v76):set_highlighted(false)
                v_u_22:get(v76):set_visible(false)
            end;
            v_u_21:set_visible(false)
        end;
        v19.behaviour_update = function(p77, p78, _) --[[ Name: behaviour_update ]] --[[ Line: 317 ]]
            --[[ Upvalues: (copy 1): p_u_15 ]]
            p77:behaviour_update_base(p78, p_u_15)
        end;
        v19.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 321 ]]
            --[[ Upvalues: (ref 1): v_u_20 ]]
            v_u_20:Destroy()
        end;
        v19.layout = function(p79) --[[ Name: layout ]] --[[ Line: 325 ]]
            --[[ Upvalues: (copy 1): p_u_16, (ref 2): v_u_20, (copy 3): v_u_22, (ref 4): v_u_21 ]]
            p79:opt_rescale_to_max_nxy(p_u_16, 0.88, 0.8, p79:get_scale())
            local v80, v81 = p79:opt_update_cframe_params(p_u_16, {
                ["PositionNXY"] = Vector2.new(0.5, 0.45),
                ["OffsetXYZ"] = p79:anchored_offset(0.5, 0.5),
                ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
            })
            if v80 == true then
                v_u_20:SetPrimaryPartCFrame(v81)
            end;
            for v82 = 1, v_u_22:count() do
                v_u_22:get(v82):layout()
            end;
            v_u_21:layout()
        end;
        local v_u_83 = 1
        local v_u_84 = 1
        v19.set_alpha = function(_, p85) --[[ Name: set_alpha ]] --[[ Line: 344 ]]
            --[[ Upvalues: (ref 1): v_u_83, (copy 2): v_u_22, (ref 3): v_u_1, (ref 4): v_u_20 ]]
            if v_u_83 ~= p85 then
                v_u_83 = p85
                for v86 = 1, v_u_22:count() do
                    v_u_22:get(v86):set_parent_alpha(v_u_83)
                end;
                v_u_1:r_set_alpha(v_u_20, v_u_83)
            end;
        end;
        v19.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 353 ]]
            --[[ Upvalues: (ref 1): v_u_83 ]]
            return v_u_83;
        end;
        v19.set_scale = function(_, p87) --[[ Name: set_scale ]] --[[ Line: 354 ]]
            --[[ Upvalues: (ref 1): v_u_84 ]]
            v_u_84 = p87
        end;
        v19.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 355 ]]
            --[[ Upvalues: (ref 1): v_u_84 ]]
            return v_u_84;
        end;
        v19.get_native_size = function(p88) --[[ Name: get_native_size ]] --[[ Line: 357 ]]
            return p88._native_size;
        end;
        v19.get_size = function(p89) --[[ Name: get_size ]] --[[ Line: 360 ]]
            return p89._size;
        end;
        v19.set_size = function(p90, p91) --[[ Name: set_size ]] --[[ Line: 363 ]]
            --[[ Upvalues: (ref 1): v_u_20 ]]
            p90._size = p91
            v_u_20.PrimaryPart.Size = Vector3.new(p91.X, p91.Y, 0)
        end;
        v19.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 367 ]]
            --[[ Upvalues: (ref 1): v_u_20 ]]
            return v_u_20.PrimaryPart.Position;
        end;
        v19.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 368 ]]
            --[[ Upvalues: (ref 1): v_u_20 ]]
            return v_u_20.PrimaryPart.SurfaceGui;
        end;
        v19.set_showing = function(_, p92) --[[ Name: set_showing ]] --[[ Line: 369 ]]
            --[[ Upvalues: (ref 1): v_u_20, (ref 2): v_u_9 ]]
            if p92 then
                v_u_20.Parent = v_u_9:get_world_ui_folder()
            else
                v_u_20.Parent = nil
            end;
        end;
        v19:cons()
        return v19;
    end
};
