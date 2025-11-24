-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:02 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Shared.AssertType)
local v_u_6 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_7 = require(game.ReplicatedStorage.Shared.Constants)
local v_u_8 = require(game.ReplicatedStorage.Shared.InputUtil)
local v_u_9 = require(game.ReplicatedStorage.Shared.CooldownDelay)
local v_u_10 = require(game.ReplicatedStorage.SPChat.Shared.SPChatMessage)
local v_u_11 = require(game.ReplicatedStorage.Lobby.NPCNametag)
local v_u_12 = require(game.ReplicatedStorage.Pets.PetDatabase)
local v_u_13 = require(game.ReplicatedStorage.Pets.PetInfoBase)
local v_u_14 = require(game.ReplicatedStorage.Shared.FlashEvery)
local v_u_15 = require(game.ReplicatedStorage.LocalShared.FrameIndex)
local v16 = {}
local function _(p17) --[[ Name: get_anim_for_id ]] --[[ Line: 24 ]]
    local l_Animation_0 = Instance.new("Animation")
    l_Animation_0.AnimationId = p17
    return l_Animation_0;
end;
local v_u_18 = v_u_3:new():add_set_from_table_list({ game.Workspace, game.Lighting })
local v_u_34 = {
    ["new"] = function(_, p_u_19, _, p_u_20, p_u_21, p_u_22) --[[ Name: new ]] --[[ Line: 36 ]]
        --[[ Upvalues: (copy 1): v_u_13, (copy 2): v_u_14, (copy 3): v_u_11, (copy 4): v_u_12, (copy 5): v_u_4, (copy 6): v_u_1, (copy 7): v_u_18 ]]
        local v23 = {
            ["is_follow_npc"] = function(_) --[[ Name: is_follow_npc ]] --[[ Line: 78 ]]
                return true;
            end,
            ["is_local_character"] = function(_) --[[ Name: is_local_character ]] --[[ Line: 79 ]]
                return false;
            end,
            ["on_local_character_play_animation"] = function(_, _, _) end
        }
        local l_Parent_0 = p_u_22.Parent
        local v_u_24 = nil
        local v_u_25 = nil
        local v_u_26 = v_u_13:get_default_pet_root_part_size()
        local v_u_27 = v_u_14:new(1.25)
        local v_u_28 = false
        local function f_cons() --[[ Name: cons ]] --[[ Line: 52 ]]
            --[[ Upvalues: (copy 1): p_u_20, (ref 2): v_u_24, (ref 3): v_u_11, (copy 4): p_u_19, (copy 5): p_u_22, (ref 6): v_u_12, (copy 7): p_u_21, (ref 8): v_u_25, (ref 9): v_u_4, (ref 10): v_u_26, (ref 11): v_u_1 ]]
            local v29 = not p_u_20 and "?" or p_u_20.Name
            v_u_24 = v_u_11:new(p_u_19)
            v_u_24:create_nametag_on_character(p_u_22, string.format("%s", v_u_12:singleton():get_name_for_petid(p_u_21)), string.format("%s\'s Mini", v29))
            v_u_24:set_position_offset(Vector3.new(0, 2, 0))
            v_u_25 = p_u_22.PrimaryPart
            if v_u_4:is_dev_build() and v_u_26 ~= v_u_25.Size then
                v_u_1:warnf("FollowNPCLocalBase(%s) initial root part size(%s)", p_u_22:GetFullName(), v_u_4:vec3_to_str(v_u_25.Size))
            end;
            v_u_26 = v_u_25.Size
            v_u_4:ptry(function() --[[ Line: 72 ]]
                --[[ Upvalues: (ref 1): p_u_22 ]]
                p_u_22.Humanoid:SetStateEnabled(Enum.HumanoidStateType.FallingDown, false)
                p_u_22.Humanoid:SetStateEnabled(Enum.HumanoidStateType.Ragdoll, false)
                p_u_22.Humanoid.AutoRotate = false
            end)
        end;
        v23.get_npc_character = function(_) --[[ Name: get_npc_character ]] --[[ Line: 80 ]]
            --[[ Upvalues: (copy 1): p_u_22 ]]
            return p_u_22;
        end;
        v23.should_remove = function(_) --[[ Name: should_remove ]] --[[ Line: 81 ]]
            --[[ Upvalues: (copy 1): p_u_22, (ref 2): v_u_4, (ref 3): v_u_18, (copy 4): p_u_20 ]]
            return (p_u_22 == nil or (v_u_4:is_child_of_parent_set(p_u_22, v_u_18) ~= true or p_u_20 == nil)) and true or p_u_20.Parent == nil;
        end;
        v23.do_remove = function(_) --[[ Name: do_remove ]] --[[ Line: 84 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_24 ]]
            v_u_4:ptry(function() --[[ Line: 85 ]]
                --[[ Upvalues: (ref 1): v_u_24 ]]
                if v_u_24 ~= nil then
                    v_u_24:do_remove()
                    v_u_24 = nil
                end;
            end)
        end;
        v23.is_visible = function(_) --[[ Name: is_visible ]] --[[ Line: 92 ]]
            --[[ Upvalues: (copy 1): p_u_22, (copy 2): l_Parent_0 ]]
            return p_u_22.Parent == l_Parent_0;
        end;
        v23.off_frame_index_check_root_part_position = function(p30, p31) --[[ Name: off_frame_index_check_root_part_position ]] --[[ Line: 94 ]]
            --[[ Upvalues: (ref 1): v_u_24 ]]
            if p30:is_visible() and v_u_24:off_frame_index_check_root_part_position(p31) then
                v_u_24:update(p31)
            end;
            return false;
        end;
        v23.update = function(p32, p33) --[[ Name: update ]] --[[ Line: 101 ]]
            --[[ Upvalues: (ref 1): v_u_24, (ref 2): v_u_28, (copy 3): v_u_27, (ref 4): v_u_25, (ref 5): v_u_26, (ref 6): v_u_4, (ref 7): v_u_1 ]]
            if p32:is_visible() then
                v_u_24:update_humanoid_root_position()
                v_u_24:update(p33)
                if v_u_28 == true then
                    v_u_27:update(p33)
                    if v_u_27:do_flash() then
                        if v_u_25.Size ~= v_u_26 then
                            if v_u_4:is_dev_build() then
                                v_u_1:puts("_recheck_root_part update size(%s) to (%s)", v_u_4:vec3_to_str(v_u_25.Size), v_u_4:vec3_to_str(v_u_26))
                            end;
                            v_u_25.Size = v_u_26
                        end;
                        v_u_28 = false
                    end;
                end;
            end;
        end;
        v23.on_transfer_network_ownership = function(_) --[[ Name: on_transfer_network_ownership ]] --[[ Line: 123 ]]
            --[[ Upvalues: (ref 1): v_u_28, (copy 2): v_u_27 ]]
            v_u_28 = true
            v_u_27:reset()
        end;
        f_cons()
        return v23;
    end
}
local v_u_54 = {
    ["new"] = function(_, p35, p36, p37, p38, p_u_39) --[[ Name: new ]] --[[ Line: 133 ]]
        --[[ Upvalues: (copy 1): v_u_34, (copy 2): v_u_4 ]]
        local v40 = v_u_34:new(p35, p36, p37, p38, p_u_39)
        local v_u_41 = nil
        local v_u_42 = nil
        local v_u_43 = nil
        local v_u_44 = nil
        local function f_cons() --[[ Name: cons ]] --[[ Line: 147 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): p_u_39, (ref 3): v_u_41, (ref 4): v_u_42, (ref 5): v_u_43 ]]
            local v_u_45 = v_u_4:get_character_humanoid(p_u_39)
            if v_u_45 then
                v_u_41 = v_u_45.RootPart
                pcall(function() --[[ Line: 151 ]]
                    --[[ Upvalues: (ref 1): v_u_42, (copy 2): v_u_45, (ref 3): v_u_43 ]]
                    local v46 = v_u_45
                    local l_Animation_1 = Instance.new("Animation")
                    l_Animation_1.AnimationId = "http://www.roblox.com/asset/?id=12989971467"
                    v_u_42 = v46:LoadAnimation(l_Animation_1)
                    local v47 = v_u_45
                    local l_Animation_2 = Instance.new("Animation")
                    l_Animation_2.AnimationId = "http://www.roblox.com/asset/?id=507777826"
                    v_u_43 = v47:LoadAnimation(l_Animation_2)
                end)
            end;
            if v_u_41 then
                v_u_4:ptry(function() --[[ Line: 158 ]]
                    --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_41 ]]
                    for _, v48 in v_u_4:get_list_of_children_of_classname(v_u_41, "AlignPosition"):key_itr() do
                        v48:Destroy()
                    end;
                    for _, v49 in v_u_4:get_list_of_children_of_classname(v_u_41, "AlignOrientation"):key_itr() do
                        v49:Destroy()
                    end;
                end)
            end;
        end;
        local l_update_0 = v40.update
        v40.update = function(p50, p51) --[[ Name: update ]] --[[ Line: 170 ]]
            --[[ Upvalues: (copy 1): l_update_0, (ref 2): v_u_41, (ref 3): v_u_43, (ref 4): v_u_42, (ref 5): v_u_44 ]]
            l_update_0(p50, p51)
            if p50:is_visible() and v_u_41 ~= nil then
                local l_Velocity_0 = v_u_41.Velocity
                local v52
                if Vector3.new(l_Velocity_0.X, 0, l_Velocity_0.Z).Magnitude > 8 then
                    v52 = v_u_43
                else
                    v52 = v_u_42
                end;
                if v_u_44 ~= v52 then
                    if v_u_44 then
                        v_u_44:Stop()
                    end;
                    if v52 then
                        v52:Play()
                    end;
                    v_u_44 = v52
                end;
            end;
        end;
        local l_do_remove_0 = v40.do_remove
        v40.do_remove = function(p53) --[[ Name: do_remove ]] --[[ Line: 196 ]]
            --[[ Upvalues: (ref 1): v_u_42, (ref 2): v_u_43, (copy 3): l_do_remove_0 ]]
            if v_u_42 then
                v_u_42:Stop()
                v_u_42:Destroy()
            end;
            v_u_42 = nil
            if v_u_43 then
                v_u_43:Stop()
                v_u_43:Destroy()
            end;
            v_u_43 = nil
            l_do_remove_0(p53)
        end;
        f_cons()
        return v40;
    end
}
local v_u_102 = {
    ["new"] = function(_, p_u_55, p56, p_u_57, p58, p_u_59) --[[ Name: new ]] --[[ Line: 209 ]]
        --[[ Upvalues: (copy 1): v_u_34, (copy 2): v_u_1, (copy 3): v_u_4, (copy 4): v_u_7, (copy 5): v_u_9, (copy 6): v_u_8 ]]
        local v_u_60 = v_u_34:new(p_u_55, p56, p_u_57, p58, p_u_59)
        local v_u_61 = nil
        local v_u_62 = nil
        local v_u_63 = nil
        local v_u_64 = nil
        local v_u_65 = nil
        local v_u_66 = nil
        local v_u_67 = nil
        local v_u_68 = nil
        local v_u_69 = nil
        local v_u_70 = nil
        local v_u_71 = nil
        local function _() --[[ Name: cons ]] --[[ Line: 228 ]]
            --[[ Upvalues: (copy 1): v_u_60, (ref 2): v_u_1 ]]
            local v72 = v_u_60:get_component_parts()
            if v72 ~= true then
                v_u_1:warnf("PlayerFollowNPCLocal cons get_component_parts(%s)", (tostring(v72)))
            end;
        end;
        v_u_60.get_component_parts = function(_) --[[ Name: get_component_parts ]] --[[ Line: 235 ]]
            --[[ Upvalues: (ref 1): v_u_66, (ref 2): v_u_4, (copy 3): p_u_57, (ref 4): v_u_61, (ref 5): v_u_7, (ref 6): v_u_62, (copy 7): p_u_59, (ref 8): v_u_63, (ref 9): v_u_64, (ref 10): v_u_65, (copy 11): p_u_55, (ref 12): v_u_67, (ref 13): v_u_68, (ref 14): v_u_69, (ref 15): v_u_1 ]]
            if v_u_66 then
                return true;
            end;
            local v73 = v_u_4:get_character_humanoid(p_u_57)
            if v73 == nil then
                return 0;
            end;
            local l_RootPart_0 = v73.RootPart
            if l_RootPart_0 == nil then
                return 1;
            end;
            v_u_61 = l_RootPart_0:FindFirstChild(v_u_7.PET_FOLLOW_ATTACHMENT_NAME)
            if v_u_61 == nil then
                return 2;
            end;
            v_u_62 = v_u_4:get_character_humanoid(p_u_59)
            v_u_63 = v_u_62.RootPart
            if v_u_63 == nil then
                return 3;
            end;
            v_u_64 = v_u_4:first_child_of_type(v_u_63, "AlignPosition")
            v_u_65 = v_u_4:first_child_of_type(v_u_63, "AlignOrientation")
            if v_u_64 == nil or v_u_65 == nil then
                return 4;
            end;
            v_u_66 = Instance.new("Attachment", p_u_55._follow_npc_manager:get_world_attach_root())
            v_u_66.Position = v_u_61.WorldPosition
            v_u_66.Orientation = v_u_61.WorldOrientation
            v_u_64.Attachment1 = v_u_66
            v_u_65.Attachment1 = v_u_66;
            (function() --[[ Name: load_animations ]] --[[ Line: 260 ]]
                --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_67, (ref 3): v_u_62, (ref 4): v_u_68, (ref 5): v_u_69, (ref 6): v_u_66, (ref 7): v_u_1 ]]
                v_u_4:ptry(function() --[[ Line: 261 ]]
                    --[[ Upvalues: (ref 1): v_u_67, (ref 2): v_u_62, (ref 3): v_u_68, (ref 4): v_u_69 ]]
                    local v74 = v_u_62
                    local l_Animation_3 = Instance.new("Animation")
                    l_Animation_3.AnimationId = "http://www.roblox.com/asset/?id=12989971467"
                    v_u_67 = v74:LoadAnimation(l_Animation_3)
                    local v75 = v_u_62
                    local l_Animation_4 = Instance.new("Animation")
                    l_Animation_4.AnimationId = "http://www.roblox.com/asset/?id=507777826"
                    v_u_68 = v75:LoadAnimation(l_Animation_4)
                    local v76 = v_u_62
                    local l_Animation_5 = Instance.new("Animation")
                    l_Animation_5.AnimationId = "http://www.roblox.com/asset/?id=507767968"
                    v_u_69 = v76:LoadAnimation(l_Animation_5)
                end)
                local function _() --[[ Name: still_needs_to_load ]] --[[ Line: 267 ]]
                    --[[ Upvalues: (ref 1): v_u_66, (ref 2): v_u_67 ]]
                    local v77
                    if v_u_66 == nil then
                        v77 = false
                    else
                        v77 = v_u_67 == nil
                    end;
                    return v77;
                end;
                local v78
                if v_u_66 == nil then
                    v78 = false
                else
                    v78 = v_u_67 == nil
                end;
                if v78 == true then
                    spawn(function() --[[ Line: 270 ]]
                        --[[ Upvalues: (ref 1): v_u_66, (ref 2): v_u_67, (ref 3): v_u_4, (ref 4): v_u_1, (ref 5): v_u_62, (ref 6): v_u_68, (ref 7): v_u_69 ]]
                        local v_u_79 = 0
                        while true do
                            if true then
                                local v80
                                if v_u_66 == nil then
                                    v80 = false
                                else
                                    v80 = v_u_67 == nil
                                end;
                            end;
                            if not v80 then
                                break;
                            end;
                            v_u_4:ptry(function() --[[ Line: 273 ]]
                                --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_79, (ref 3): v_u_67, (ref 4): v_u_62, (ref 5): v_u_68, (ref 6): v_u_69 ]]
                                v_u_1:warnf("LocalPlayerFollowNPCLocal:get_component_parts load_animations still_needs_to_load, retrying(%d)", v_u_79)
                                local v81 = v_u_62
                                local l_Animation_6 = Instance.new("Animation")
                                l_Animation_6.AnimationId = "http://www.roblox.com/asset/?id=12989971467"
                                v_u_67 = v81:LoadAnimation(l_Animation_6)
                                local v82 = v_u_62
                                local l_Animation_7 = Instance.new("Animation")
                                l_Animation_7.AnimationId = "http://www.roblox.com/asset/?id=507777826"
                                v_u_68 = v82:LoadAnimation(l_Animation_7)
                                local v83 = v_u_62
                                local l_Animation_8 = Instance.new("Animation")
                                l_Animation_8.AnimationId = "http://www.roblox.com/asset/?id=507767968"
                                v_u_69 = v83:LoadAnimation(l_Animation_8)
                            end)
                            local v84 = v_u_79 + 1
                            if v84 > 20 then
                                break;
                            end;
                            wait(0.25)
                            v_u_79 = v84
                        end;
                    end)
                end;
            end)()
            return true;
        end;
        local function _() --[[ Name: has_all_components ]] --[[ Line: 291 ]]
            --[[ Upvalues: (copy 1): p_u_59, (ref 2): v_u_4, (ref 3): v_u_61, (ref 4): v_u_63, (ref 5): v_u_64, (ref 6): v_u_65, (ref 7): v_u_66 ]]
            local v85
            if p_u_59.PrimaryPart == nil or (v_u_4:get_local_character_humanoid_rootpart() == nil or (v_u_61 == nil or (v_u_63 == nil or (v_u_64 == nil or v_u_65 == nil)))) then
                v85 = false
            else
                v85 = v_u_66 ~= nil
            end;
            return v85;
        end;
        v_u_60.on_local_character_play_animation = function(_, p_u_86, p_u_87) --[[ Name: on_local_character_play_animation ]] --[[ Line: 302 ]]
            --[[ Upvalues: (copy 1): p_u_59, (ref 2): v_u_4, (ref 3): v_u_61, (ref 4): v_u_63, (ref 5): v_u_64, (ref 6): v_u_65, (ref 7): v_u_66, (ref 8): v_u_70, (ref 9): v_u_62, (ref 10): v_u_71 ]]
            local v88
            if p_u_59.PrimaryPart == nil or (v_u_4:get_local_character_humanoid_rootpart() == nil or (v_u_61 == nil or (v_u_63 == nil or (v_u_64 == nil or v_u_65 == nil)))) then
                v88 = false
            else
                v88 = v_u_66 ~= nil
            end;
            if v88 == true then
                v_u_4:ptry(function() --[[ Line: 304 ]]
                    --[[ Upvalues: (ref 1): v_u_70, (ref 2): v_u_62, (copy 3): p_u_86, (ref 4): v_u_71, (copy 5): p_u_87 ]]
                    v_u_70 = v_u_62:LoadAnimation(p_u_86)
                    if v_u_71 ~= nil then
                        v_u_71:Stop()
                    end;
                    v_u_71 = v_u_70
                    v_u_70:Play()
                    if p_u_87 ~= nil then
                        v_u_70.TimePosition = p_u_87
                    end;
                end)
            end;
        end;
        v_u_60.is_local_character = function(_) --[[ Name: is_local_character ]] --[[ Line: 317 ]]
            return true;
        end;
        local l_update_1 = v_u_60.update
        local v_u_89 = v_u_9:new()
        v_u_60.update = function(p90, p91) --[[ Name: update ]] --[[ Line: 321 ]]
            --[[ Upvalues: (copy 1): l_update_1, (copy 2): p_u_59, (ref 3): v_u_4, (ref 4): v_u_61, (ref 5): v_u_63, (ref 6): v_u_64, (ref 7): v_u_65, (ref 8): v_u_66, (ref 9): v_u_62, (copy 10): v_u_89, (copy 11): p_u_55, (ref 12): v_u_70, (ref 13): v_u_69, (ref 14): v_u_68, (ref 15): v_u_67, (ref 16): v_u_71, (ref 17): v_u_8, (ref 18): v_u_1 ]]
            l_update_1(p90, p91)
            local v92
            if p_u_59.PrimaryPart == nil or (v_u_4:get_local_character_humanoid_rootpart() == nil or (v_u_61 == nil or (v_u_63 == nil or (v_u_64 == nil or v_u_65 == nil)))) then
                v92 = false
            else
                v92 = v_u_66 ~= nil
            end;
            if v92 == true then
                if v_u_62:GetState() ~= Enum.HumanoidStateType.Running then
                    v_u_62:ChangeState(Enum.HumanoidStateType.Running)
                end;
                local l_Position_0 = v_u_63.Position
                local l_WorldPosition_0 = v_u_61.WorldPosition
                local l_Magnitude_0 = (l_Position_0 - l_WorldPosition_0).Magnitude
                v_u_89:update(p91)
                local v93 = false
                if l_Magnitude_0 > 25 and v_u_89:is_on_cooldown() ~= true then
                    v_u_89:add_cooldown(2)
                    p_u_59:SetPrimaryPartCFrame(CFrame.lookAt(v_u_61.WorldPosition, v_u_4:get_localplayer_cframe().p))
                elseif l_Magnitude_0 > 10 then
                    v_u_66.Position = l_WorldPosition_0
                    v93 = true
                elseif l_Magnitude_0 < 7.5 then
                    v_u_66.Position = l_Position_0
                else
                    v93 = true
                end;
                local l_Velocity_1 = v_u_63.Velocity
                local v94 = Vector3.new(l_Velocity_1.X, 0, l_Velocity_1.Z)
                if v93 then
                    v93 = v94.Magnitude > 1
                end;
                if v93 == true then
                    v_u_66.CFrame = CFrame.lookAt(v_u_66.Position, v_u_66.Position + l_Velocity_1)
                end;
                local v95 = p_u_55._lobby_join:get_lobby()
                local v96
                if v95 == nil then
                    v96 = false
                else
                    v96 = v95:is_control_pressed()
                end;
                local v97
                if v_u_70 == nil or v96 == true then
                    if math.abs(l_Velocity_1.Y) > 8 then
                        v97 = v_u_69
                    elseif v93 then
                        v97 = v_u_68
                    else
                        v97 = v_u_67
                    end;
                else
                    v97 = v_u_70
                end;
                if v_u_71 ~= v97 then
                    if v_u_71 then
                        v_u_71:Stop()
                        if v_u_71 == v_u_70 then
                            v_u_70:Destroy()
                            v_u_70 = nil
                        end;
                    end;
                    if v97 then
                        v97:Play()
                    end;
                    v_u_71 = v97
                end;
                if v_u_4:is_dev_build() and p_u_55._input:control_just_pressed(v_u_8.KEY_DEBUG_4) then
                    local v98 = p_u_55._menus:get_top_element()
                    if (v98 == nil and true or v98:swallows_input()) == false then
                        local _, v99 = v_u_4:get_local_character_humanoid_rootpart()
                        v_u_1:puts("\tPlayerFollowNPCLocal NPC(%s) Dist(%.2f) NPCVel(%s) NPCVecPlane(%s) PlayerVel(%s)", p_u_59.Name, l_Magnitude_0, v_u_4:vec3_to_str(l_Velocity_1), v_u_4:vec3_to_str(v94), v_u_4:vec3_to_str(v99.Velocity))
                    end;
                end;
            end;
        end;
        local l_do_remove_1 = v_u_60.do_remove
        v_u_60.do_remove = function(p100) --[[ Name: do_remove ]] --[[ Line: 428 ]]
            --[[ Upvalues: (ref 1): v_u_67, (ref 2): v_u_68, (ref 3): v_u_69, (ref 4): v_u_70, (copy 5): l_do_remove_1, (ref 6): v_u_66, (ref 7): v_u_61, (ref 8): v_u_62, (ref 9): v_u_63, (ref 10): v_u_64, (ref 11): v_u_65 ]]
            if v_u_67 then
                v_u_67:Stop()
                v_u_67:Destroy()
            end;
            v_u_67 = nil
            if v_u_68 then
                v_u_68:Stop()
                v_u_68:Destroy()
            end;
            v_u_68 = nil
            if v_u_69 then
                v_u_69:Stop()
                v_u_69:Destroy()
            end;
            v_u_69 = nil
            if v_u_70 then
                v_u_70:Stop()
                v_u_70:Destroy()
            end;
            v_u_70 = nil
            l_do_remove_1(p100)
            v_u_66:Destroy()
            v_u_66 = nil
            v_u_61 = nil
            v_u_62 = nil
            v_u_63 = nil
            v_u_64 = nil
            v_u_65 = nil
        end;
        local v101 = v_u_60:get_component_parts()
        if v101 ~= true then
            v_u_1:warnf("PlayerFollowNPCLocal cons get_component_parts(%s)", (tostring(v101)))
        end;
        return v_u_60;
    end
}
v16.new = function(_, p_u_103) --[[ Name: new ]] --[[ Line: 453 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_9, (copy 3): v_u_3, (copy 4): v_u_5, (copy 5): v_u_1, (copy 6): v_u_4, (copy 7): v_u_102, (copy 8): v_u_54, (copy 9): v_u_15, (copy 10): v_u_6, (copy 11): v_u_8, (copy 12): v_u_10 ]]
    local v104 = {}
    local v_u_105 = v_u_2:new()
    v104.get_active_follow_npcs = function(_) --[[ Name: get_active_follow_npcs ]] --[[ Line: 457 ]]
        --[[ Upvalues: (copy 1): v_u_105 ]]
        return v_u_105;
    end;
    local v_u_106 = nil
    local v_u_107 = nil
    local v_u_108 = nil
    v104.get_world_attach_root = function(_) --[[ Name: get_world_attach_root ]] --[[ Line: 463 ]]
        --[[ Upvalues: (ref 1): v_u_106 ]]
        return v_u_106;
    end;
    v104.get_follow_npc_root = function(_) --[[ Name: get_follow_npc_root ]] --[[ Line: 464 ]]
        --[[ Upvalues: (ref 1): v_u_107 ]]
        return v_u_107;
    end;
    local v_u_109 = v_u_9:new()
    local v_u_110 = v_u_3:new()
    v104.cons = function(_) --[[ Name: cons ]] --[[ Line: 470 ]]
        --[[ Upvalues: (copy 1): v_u_109, (ref 2): v_u_107, (ref 3): v_u_108, (ref 4): v_u_106, (copy 5): p_u_103, (ref 6): v_u_5, (ref 7): v_u_1, (copy 8): v_u_110, (ref 9): v_u_4, (copy 10): v_u_105, (ref 11): v_u_102, (ref 12): v_u_54 ]]
        v_u_109:add_cooldown(5)
        v_u_107 = game.Workspace.LobbyFollowNPCs
        v_u_108 = Instance.new("Model", game.Workspace)
        v_u_108.Name = "LocalNPCFollowRoot"
        v_u_106 = Instance.new("Part", game.Workspace)
        v_u_106.Name = "WorldAttachRoot"
        v_u_106.Anchored = true
        v_u_106.CanCollide = false
        v_u_106.Transparency = 1
        p_u_103._evt:wait_on_event(v_u_5.EVT_Lobby_ServerNotifyFollowNPCCreate, function(p111) --[[ Line: 483 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_110, (ref 3): v_u_4, (ref 4): v_u_108, (ref 5): v_u_105, (ref 6): v_u_102, (ref 7): p_u_103, (ref 8): v_u_54 ]]
            for _, v112 in pairs(p111) do
                local l_PlayerID_0 = v112.PlayerID
                local l_PlayerCharacter_0 = v112.PlayerCharacter
                local l_PetID_0 = v112.PetID
                local l_NPCCharacter_0 = v112.NPCCharacter
                if l_PlayerCharacter_0 == nil or (l_NPCCharacter_0 == nil or (l_PlayerCharacter_0.PrimaryPart == nil or l_NPCCharacter_0.PrimaryPart == nil)) then
                    v_u_1:warnf("EVT_Lobby_ServerNotifyFollowNPCCreate npc_character or player_character PrimaryPart is nil, skipping")
                elseif v_u_110:contains(l_NPCCharacter_0) ~= true then
                    if l_PlayerID_0 == v_u_4:get_local_userid() then
                        l_NPCCharacter_0.Parent = v_u_108
                        v_u_105:push_back(v_u_102:new(p_u_103, l_PlayerID_0, l_PlayerCharacter_0, l_PetID_0, l_NPCCharacter_0))
                    else
                        v_u_105:push_back(v_u_54:new(p_u_103, l_PlayerID_0, l_PlayerCharacter_0, l_PetID_0, l_NPCCharacter_0))
                    end;
                end;
            end;
        end)
        p_u_103._evt:wait_on_event(v_u_5.EVT_Lobby_ServerNotifyTransferNPCNetworkOwnership, function(p113) --[[ Line: 505 ]]
            --[[ Upvalues: (ref 1): v_u_105 ]]
            for _, v114 in v_u_105:key_itr() do
                if v114:get_npc_character() == p113 then
                    v114:on_transfer_network_ownership()
                end;
            end;
        end)
    end;
    v104.set_npcs_visible = function(_, p115) --[[ Name: set_npcs_visible ]] --[[ Line: 514 ]]
        --[[ Upvalues: (ref 1): v_u_107 ]]
        if p115 == true then
            v_u_107.Parent = game.Workspace
        else
            v_u_107.Parent = game.Lighting
        end;
    end;
    v104.set_local_npcs_visible = function(_, p116) --[[ Name: set_local_npcs_visible ]] --[[ Line: 522 ]]
        --[[ Upvalues: (ref 1): v_u_108 ]]
        if p116 == true then
            v_u_108.Parent = game.Workspace
        else
            v_u_108.Parent = game.Lighting
        end;
    end;
    local l_FollowNPC_0 = v_u_15.Test.FollowNPC
    v104.update = function(_, p117) --[[ Name: update ]] --[[ Line: 531 ]]
        --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_15, (copy 3): l_FollowNPC_0, (copy 4): v_u_105, (copy 5): p_u_103, (ref 6): v_u_4, (ref 7): v_u_8, (ref 8): v_u_1, (ref 9): v_u_10, (copy 10): v_u_110, (ref 11): v_u_2, (copy 12): v_u_109, (ref 13): v_u_107, (ref 14): v_u_5 ]]
        if v_u_6.DebugMinisActive == true then
            local v118 = v_u_15:singleton()
            if v118:should_run(l_FollowNPC_0) == false then
                for _, v119 in v_u_105:key_itr() do
                    v119:off_frame_index_check_root_part_position(p117)
                end;
            else
                local v120 = v118:get_test_state(l_FollowNPC_0)
                local v_u_121 = v120:get_dt_scale()
                p_u_103._input:set_frame_index_state(v120)
                if v_u_4:is_dev_build() and (p_u_103._input:control_just_pressed(v_u_8.KEY_DEBUG_4) and p_u_103._menus:top_menu_swallows_input() == false) then
                    local v122 = 0
                    for _, v123 in v_u_105:key_itr() do
                        if v123:is_local_character() then
                            v122 = v122 + 1
                        end;
                    end;
                    local v124 = string.format("LocalLobbyFollowNPCManager _active_follow_npcs(%d) _local(%d)", v_u_105:count(), v122)
                    v_u_1:puts(v124)
                    p_u_103._chat:get_system_channel():add_message_to_channel(v_u_10:new(v124))
                end;
                v_u_110:clear()
                v_u_2:for_each(v_u_105, function(p125) --[[ Line: 558 ]]
                    --[[ Upvalues: (ref 1): v_u_121 ]]
                    p125:update(v_u_121)
                end)
                v_u_2:remove_if(v_u_105, function(p126) --[[ Line: 561 ]]
                    --[[ Upvalues: (ref 1): v_u_110 ]]
                    local v127 = p126:should_remove()
                    if v127 then
                        p126:do_remove()
                        return v127;
                    else
                        v_u_110:add_set(p126:get_npc_character())
                        return v127;
                    end;
                end)
                if p_u_103._lobby_join:get_lobby() ~= nil then
                    v_u_109:update(v_u_121)
                    if v_u_109:is_on_cooldown() ~= true then
                        v_u_109:add_cooldown(5)
                        local v128 = v_u_2:new(v_u_107:GetChildren())
                        local v129 = v_u_2:new()
                        for _, v130 in v128:key_itr() do
                            if v_u_110:contains(v130) ~= true then
                                v129:push_back(v130)
                            end;
                        end;
                        if v129:count() > 0 then
                            p_u_103._evt:fire_event_to_server(v_u_5.EVT_Lobby_ClientRequestInfoForCharacters, v129:get_table())
                        end;
                    end;
                end;
                p_u_103._input:set_frame_index_state(nil)
            end;
        else
            return;
        end;
    end;
    v104.on_local_character_play_animation = function(_, p_u_131, p_u_132) --[[ Name: on_local_character_play_animation ]] --[[ Line: 592 ]]
        --[[ Upvalues: (ref 1): v_u_2, (copy 2): v_u_105 ]]
        v_u_2:for_each(v_u_105, function(p133) --[[ Line: 593 ]]
            --[[ Upvalues: (copy 1): p_u_131, (copy 2): p_u_132 ]]
            p133:on_local_character_play_animation(p_u_131, p_u_132)
        end)
    end;
    v104.is_character_managed_local_character = function(_, p_u_134) --[[ Name: is_character_managed_local_character ]] --[[ Line: 598 ]]
        --[[ Upvalues: (ref 1): v_u_2, (copy 2): v_u_105 ]]
        local v_u_135 = false
        local v_u_136 = nil
        v_u_2:for_each(v_u_105, function(p137) --[[ Line: 601 ]]
            --[[ Upvalues: (copy 1): p_u_134, (ref 2): v_u_136, (ref 3): v_u_135 ]]
            if p137:get_npc_character() == p_u_134 then
                v_u_136 = p137
                v_u_135 = p137:is_local_character()
                return false;
            end;
        end)
        return v_u_135, v_u_136;
    end;
    v104.character_notify_cleanup = function(_, p_u_138) --[[ Name: character_notify_cleanup ]] --[[ Line: 611 ]]
        --[[ Upvalues: (ref 1): v_u_2, (copy 2): v_u_105 ]]
        local v_u_139 = false
        v_u_2:remove_if(v_u_105, function(p140) --[[ Line: 613 ]]
            --[[ Upvalues: (copy 1): p_u_138, (ref 2): v_u_139 ]]
            local v141 = p140:get_npc_character() == p_u_138
            if v141 then
                v_u_139 = true
                p140:do_remove()
            end;
            return v141;
        end)
        return v_u_139;
    end;
    v104:cons()
    return v104;
end;
return v16;
